using Mono.Cecil;

namespace MozaikPatcher;

/// <summary>
/// Returns placeholder assemblies for unresolved references so in-memory IL edits can be written
/// without a full GAC / Mozaik install (browser uploads and offline patching).
/// </summary>
internal sealed class StubAssemblyResolver : IAssemblyResolver
{
    private readonly Dictionary<string, AssemblyDefinition> _cache = new(StringComparer.Ordinal);

    public AssemblyDefinition Resolve(AssemblyNameReference name)
        => Resolve(name, new ReaderParameters());

    public AssemblyDefinition Resolve(AssemblyNameReference name, ReaderParameters parameters)
    {
        var key = name.FullName;
        if (_cache.TryGetValue(key, out var cached))
            return cached;

        var assemblyName = new AssemblyNameDefinition(name.Name, name.Version ?? new Version(0, 0, 0, 0));
        var assembly = AssemblyDefinition.CreateAssembly(assemblyName, name.Name, ModuleKind.Dll);
        _cache[key] = assembly;
        return assembly;
    }

    public void Dispose()
    {
        foreach (var assembly in _cache.Values)
            assembly.Dispose();
        _cache.Clear();
    }
}
