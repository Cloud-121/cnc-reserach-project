using Mono.Cecil;
using Mono.Cecil.Cil;

namespace MozaikPatcher;

internal sealed class PatchResult
{
    public bool Success { get; init; }
    public string[] Messages { get; init; } = [];
    public byte[]? PatchedExe { get; init; }
    public byte[]? PatchedDll { get; init; }
    public string? Error { get; init; }
}

internal static class PatchEngine
{
    private const int SuccessMagic = 7675;

    internal static PatchResult Patch(byte[] exeBytes, byte[] dllBytes)
    {
        var messages = new List<string>();

        try
        {
            if (exeBytes.Length < 2 || exeBytes[0] != 'M' || exeBytes[1] != 'Z')
                throw new InvalidOperationException("Mozaik.exe does not look like a PE file.");
            if (dllBytes.Length < 2 || dllBytes[0] != 'M' || dllBytes[1] != 'Z')
                throw new InvalidOperationException("MozaikData.dll does not look like a PE file.");

            var patchedExe = PatchExe(exeBytes, messages);
            var patchedDll = PatchDll(dllBytes, messages);

            messages.Add("Patch complete.");
            return new PatchResult
            {
                Success = true,
                Messages = messages.ToArray(),
                PatchedExe = patchedExe,
                PatchedDll = patchedDll,
            };
        }
        catch (Exception ex)
        {
            return new PatchResult
            {
                Success = false,
                Messages = messages.ToArray(),
                Error = ex.Message,
            };
        }
    }

    private static void PrepareModuleForWrite(ModuleDefinition module)
    {
        foreach (var type in AllTypes(module))
        {
            foreach (var method in type.Methods)
            {
                foreach (var parameter in method.Parameters)
                    parameter.Constant = null;
            }

            foreach (var field in type.Fields)
                field.Constant = null;
        }
    }

    private static byte[] WriteModule(ModuleDefinition module)
    {
        PrepareModuleForWrite(module);
        using var outputStream = new MemoryStream();
        module.Write(outputStream);
        return outputStream.ToArray();
    }

    private static ReaderParameters CreateReadParameters(StubAssemblyResolver resolver)
    {
        return new ReaderParameters
        {
            ReadWrite = true,
            AssemblyResolver = resolver,
            MetadataResolver = new StubMetadataResolver(resolver),
        };
    }

    private static byte[] PatchExe(byte[] input, List<string> messages)
    {
        using var inputStream = new MemoryStream(input, writable: false);
        using var resolver = new StubAssemblyResolver();

        var module = ModuleDefinition.ReadModule(inputStream, CreateReadParameters(resolver));

        try
        {
            var gs = GetGsMethod(module);
            PatchStartupGate(gs, messages);
            PatchDateGate(gs, messages);
            gs.Body.MaxStackSize = Math.Max(gs.Body.MaxStackSize, 16);
            messages.Add("Patched startup gate in Mozaik.exe");
            return WriteModule(module);
        }
        finally
        {
            module.Dispose();
        }
    }

    private static byte[] PatchDll(byte[] input, List<string> messages)
    {
        using var inputStream = new MemoryStream(input, writable: false);
        using var resolver = new StubAssemblyResolver();

        var module = ModuleDefinition.ReadModule(inputStream, CreateReadParameters(resolver));

        try
        {
            var em = AllTypes(module).FirstOrDefault(t => t.Name == "em")
                ?? throw new InvalidOperationException("Type em not found in MozaikData.dll");

            var validator = em.Methods.FirstOrDefault(m =>
                m.Name == "a"
                && m.Parameters.Count == 3
                && m.ReturnType.Name == "Int16")
                ?? throw new InvalidOperationException("Validator em.a(string, bool, ref bool) not found");

            PatchValidator(validator);
            messages.Add("Patched validator in MozaikData.dll");
            return WriteModule(module);
        }
        finally
        {
            module.Dispose();
        }
    }

    private static IEnumerable<TypeDefinition> AllTypes(ModuleDefinition module)
    {
        foreach (var type in module.Types)
        {
            yield return type;
            foreach (var nested in AllNested(type))
                yield return nested;
        }
    }

    private static IEnumerable<TypeDefinition> AllNested(TypeDefinition type)
    {
        foreach (var nested in type.NestedTypes)
        {
            yield return nested;
            foreach (var child in AllNested(nested))
                yield return child;
        }
    }

    private static MethodDefinition GetGsMethod(ModuleDefinition module)
    {
        var sh = AllTypes(module).FirstOrDefault(t => t.Name == "sh")
            ?? throw new InvalidOperationException("Type sh not found");

        return sh.Methods.FirstOrDefault(m =>
            m.Name == "gs" && m.Parameters.Count == 2 && m.HasBody)
            ?? throw new InvalidOperationException("Method sh.gs(object, EventArgs) not found");
    }

    private static void PatchValidator(MethodDefinition validator)
    {
        validator.Body.Instructions.Clear();
        validator.Body.Variables.Clear();
        validator.Body.ExceptionHandlers.Clear();
        var il = validator.Body.GetILProcessor();
        il.Append(il.Create(OpCodes.Ldc_I4, SuccessMagic));
        il.Append(il.Create(OpCodes.Ret));
    }

    private static void ForceUnconditionalBranch(MethodDefinition method, Instruction branch)
    {
        var il = method.Body.GetILProcessor();
        il.InsertBefore(branch, il.Create(OpCodes.Pop));
        branch.OpCode = OpCodes.Br_S;
    }

    private static void PatchStartupGate(MethodDefinition gs, List<string> messages)
    {
        for (var i = 0; i < gs.Body.Instructions.Count; i++)
        {
            var ins = gs.Body.Instructions[i];
            if (ins.OpCode != OpCodes.Call || ins.Operand is not MethodReference mr
                || mr.Name != "CompareString" || mr.DeclaringType.Name != "Operators")
                continue;

            var prev = i >= 1 ? gs.Body.Instructions[i - 1] : null;
            if (prev?.OpCode != OpCodes.Ldc_I4_0)
                continue;

            for (var j = i + 1; j < Math.Min(i + 3, gs.Body.Instructions.Count); j++)
            {
                var br = gs.Body.Instructions[j];
                if (br.OpCode != OpCodes.Brtrue_S && br.OpCode != OpCodes.Brtrue
                    && br.OpCode != OpCodes.Brfalse_S && br.OpCode != OpCodes.Brfalse)
                    continue;

                var target = (Instruction)br.Operand!;
                ForceUnconditionalBranch(gs, br);
                messages.Add($"Patched startup empty-code branch at {br.Offset:X4} -> {target.Offset:X4}");
                return;
            }
        }

        throw new InvalidOperationException("Could not locate startup empty-code branch in sh.gs");
    }

    private static void PatchDateGate(MethodDefinition gs, List<string> messages)
    {
        var ins = gs.Body.Instructions;
        for (var i = 0; i < ins.Count - 3; i++)
        {
            if (ins[i].OpCode != OpCodes.Ldfld || ins[i].Operand is not FieldReference fr
                || fr.Name is not ("b8" or "m_b8"))
                continue;

            var br = ins[i + 1];
            if (br.OpCode != OpCodes.Brtrue_S && br.OpCode != OpCodes.Brtrue)
                continue;

            if (ins[i + 2].OpCode != OpCodes.Ldarg_0)
                continue;
            if (ins[i + 3].OpCode != OpCodes.Call && ins[i + 3].OpCode != OpCodes.Callvirt)
                continue;
            if (ins[i + 3].Operand is not MethodReference closeMr || closeMr.Name != "Close")
                continue;

            ForceUnconditionalBranch(gs, br);
            messages.Add($"Patched date gate branch at {br.Offset:X4}");
            return;
        }

        messages.Add("Warning: date gate branch not patched");
    }
}
