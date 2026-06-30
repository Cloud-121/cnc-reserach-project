using System.Runtime.InteropServices.JavaScript;
using System.Text.Json;

namespace MozaikPatcher;

public partial class PatcherInterop
{
    [JSExport]
    internal static string PatchAssemblies(byte[] exeBytes, byte[] dllBytes)
    {
        var result = PatchEngine.Patch(exeBytes, dllBytes);
        return JsonSerializer.Serialize(new
        {
            success = result.Success,
            messages = result.Messages,
            error = result.Error,
            patchedExe = result.PatchedExe is null ? null : Convert.ToBase64String(result.PatchedExe),
            patchedDll = result.PatchedDll is null ? null : Convert.ToBase64String(result.PatchedDll),
        });
    }
}
