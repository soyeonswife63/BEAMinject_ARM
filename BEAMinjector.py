"""
BEAMinjector module, made for BEAMinject

For usage as a module, check out the
"# Modify values for imported usage" section
of the code, and then configure accordingly
"""
__version__ = "0.2.1"

import os
import sys
import ctypes
import librosewater
import librosewater.module
import platform
import psutil

# Modify values for imported usage
launchmc = True
if sys.stdout:
    write_logs = sys.stdout.write
else:
    # sys.stdout doesn't exist, so we can just write a dummy function
    def write_logs(*args, **kwargs):
        pass
quitfunc = sys.exit

# Identify for inject_buildstr.py
buildstr = "custombuild"

i64_patch = [
    (
        bytes.fromhex("39 9E C8 00 00 00 0F 95 C1 88 0F 8B"),
        bytes.fromhex("39 9E C8 00 00 00 B1 00 90 88 0F 8B")
    ),
    (
        bytes.fromhex("FF EB 05 8A 49 61 88 0A 8B CB E8"),
        bytes.fromhex("FF EB 05 B1 00 90 88 0A 8B CB E8")
    )
]

i32_patch = [
    (
        bytes.fromhex("FF EB 08 39 77 74 0F 95 C1 88 08 8B"),
        bytes.fromhex("FF EB 08 39 77 74 B1 00 90 88 08 8B")
    ),
    (
        bytes.fromhex("FF EB 08 8B 4D 08 8A 49 31 88 08 8B"),
        bytes.fromhex("FF EB 08 8B 4D 08 B1 00 90 88 08 8B")
    )
]

def get_patches_for_platform() -> list:
    """
    Returns a list of patches for the target platform.
    Raises NotImplementedError for unavailable targets.
    """
    cpuarch = platform.machine().casefold()
    match cpuarch:
        case "i386":
            return i32_patch
        case "i686":
            return i32_patch
        case "amd64":
            return i64_patch
        case "x86_64":
            return i64_patch
        case _:
            raise NotImplementedError("unsupported architecture %s" % cpuarch)

def main():
    if launchmc:
        write_logs("= Launching Minecraft UWP\n")
        os.system("powershell.exe explorer.exe shell:AppsFolder\\$(get-appxpackage -name Microsoft.MinecraftUWP ^| select -expandproperty PackageFamilyName)!App")
    write_logs("= Waiting for Minecraft to launch... ")
    process = None
    while not process:
        for proc in psutil.process_iter():
            try:
                if "Minecraft.Windows.exe" in proc.name():
                    process = proc
            except psutil.NoSuchProcess:
                pass
    write_logs(f"found at PID {process.pid}! Proceeding...\n")
    PID = process.pid
    process_handle = ctypes.windll.kernel32.OpenProcess(librosewater.PROCESS_ALL_ACCESS, False, PID)
    
    # Get module address
    write_logs("= Waiting for module... ")
    try:
        module_address, _ = librosewater.module.wait_for_module(process_handle, "Windows.ApplicationModel.Store.dll")
    except librosewater.exceptions.QueryError:
        write_logs(f"! Couldn't wait for module, did Minecraft close?\n")
        return quitfunc()
    write_logs(f"found at {hex(module_address)}!\n")

    # Dump module to variable
    write_logs("= Dumping module... ")
    try:
        data = librosewater.module.dump_module(process_handle, module_address)
    except librosewater.exceptions.ReadWriteError:
        write_logs(f"\n! Couldn't dump module, did Minecraft close?\n")
        return quitfunc()
    write_logs(f"done (read {len(data[1])} bytes)!\n")

    # Inject new module data
    write_logs("= Patching module... ")
    new_data = data[1]
    for patch in get_patches_for_platform():
        new_data = new_data.replace(patch[0], patch[1])
    write_logs("done!\n")

    write_logs("= Injecting module... ")
    try:
        librosewater.module.inject_module(process_handle, module_address, new_data)
    except librosewater.exceptions.ReadWriteError:
        write_logs(f"\n! Couldn't inject module, did Minecraft close?\n")
        return quitfunc()
    write_logs(f"done (wrote {len(new_data)} bytes)!\n")

    return quitfunc()

if __name__ == "__main__":
    main()
