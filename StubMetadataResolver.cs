using Mono.Cecil;

namespace MozaikPatcher;

internal sealed class StubMetadataResolver : MetadataResolver
{
    public StubMetadataResolver(IAssemblyResolver assemblyResolver)
        : base(assemblyResolver)
    {
    }

    public override TypeDefinition Resolve(TypeReference type)
    {
        if (type == null)
            throw new ArgumentNullException(nameof(type));

        try
        {
            return base.Resolve(type);
        }
        catch (Exception ex) when (ex is ResolutionException or AssemblyResolutionException)
        {
            return GetOrCreateStubType(type);
        }
    }

    public override FieldDefinition Resolve(FieldReference field)
    {
        try
        {
            return base.Resolve(field);
        }
        catch (ResolutionException)
        {
            var declaringType = Resolve(field.DeclaringType);
            var stub = new FieldDefinition(
                field.Name,
                FieldAttributes.Public,
                field.FieldType);
            declaringType.Fields.Add(stub);
            return stub;
        }
    }

    public override MethodDefinition Resolve(MethodReference method)
    {
        try
        {
            return base.Resolve(method);
        }
        catch (ResolutionException)
        {
            var declaringType = Resolve(method.DeclaringType);
            var stub = new MethodDefinition(
                method.Name,
                MethodAttributes.Public | MethodAttributes.Static,
                method.ReturnType);
            foreach (var parameter in method.Parameters)
                stub.Parameters.Add(new ParameterDefinition(parameter.Name, parameter.Attributes, parameter.ParameterType));
            declaringType.Methods.Add(stub);
            return stub;
        }
    }

    private readonly Dictionary<string, TypeDefinition> _types = new(StringComparer.Ordinal);

    private TypeDefinition GetOrCreateStubType(TypeReference type)
    {
        var key = type.FullName;
        if (_types.TryGetValue(key, out var existing))
            return existing;

        var assembly = ResolveAssembly(type);
        var module = assembly.MainModule;
        var objectRef = module.TypeSystem.Object;

        TypeDefinition declaringType;
        if (type.DeclaringType is not null)
        {
            declaringType = GetOrCreateStubType(type.DeclaringType);
        }
        else
        {
            declaringType = new TypeDefinition(
                type.Namespace ?? string.Empty,
                type.Name,
                TypeAttributes.Public | TypeAttributes.Class,
                objectRef);
            module.Types.Add(declaringType);
        }

        if (type.DeclaringType is not null)
        {
            var nested = new TypeDefinition(
                string.Empty,
                type.Name,
                TypeAttributes.NestedPublic | TypeAttributes.Sealed,
                objectRef);
            nested.DeclaringType = declaringType;
            declaringType.NestedTypes.Add(nested);
            declaringType = nested;
        }

        _types[key] = declaringType;
        return declaringType;
    }

    private AssemblyDefinition ResolveAssembly(TypeReference type)
    {
        if (type.Scope is AssemblyNameReference assemblyName)
            return AssemblyResolver.Resolve(assemblyName);

        if (type.Scope is ModuleDefinition moduleDefinition)
            return moduleDefinition.Assembly;

        throw new ResolutionException(type);
    }
}
