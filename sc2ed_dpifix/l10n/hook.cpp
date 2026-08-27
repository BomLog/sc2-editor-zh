#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <unordered_map>

namespace {

constexpr std::uintptr_t kFallbackRva = 0x297B70;
constexpr std::uintptr_t kCallSiteRva = 0x404B57;
constexpr unsigned char kFallbackSignature[] = {
    0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x40,
};
constexpr unsigned char kCallSignature[] = {0xE8, 0x14, 0x30, 0xE9, 0xFF};

struct StringRange {
    const char* begin;
    const char* end;
};

using FallbackName = void(__fastcall*)(void*, const StringRange*, void*);

HMODULE g_module = nullptr;
FallbackName g_original = nullptr;
std::unordered_map<std::string, std::string> g_names;
std::wstring g_directory;

std::wstring ModuleDirectory() {
    wchar_t path[MAX_PATH] = {};
    const DWORD length = GetModuleFileNameW(g_module, path, MAX_PATH);
    if (!length || length >= MAX_PATH) {
        return L".";
    }
    std::wstring result(path, length);
    const auto slash = result.find_last_of(L"\\/");
    return slash == std::wstring::npos ? L"." : result.substr(0, slash);
}

void Log(const std::string& message) {
    if (g_directory.empty()) {
        g_directory = ModuleDirectory();
    }
    const std::wstring path = g_directory + L"\\SC2EditorDependencyL10n.log";
    std::ofstream out(path.c_str(), std::ios::app);
    if (!out) {
        return;
    }
    SYSTEMTIME now{};
    GetLocalTime(&now);
    out << '[' << now.wYear << '-';
    if (now.wMonth < 10) out << '0';
    out << now.wMonth << '-';
    if (now.wDay < 10) out << '0';
    out << now.wDay << ' ';
    if (now.wHour < 10) out << '0';
    out << now.wHour << ':';
    if (now.wMinute < 10) out << '0';
    out << now.wMinute << ':';
    if (now.wSecond < 10) out << '0';
    out << now.wSecond << "] " << message << '\n';
}

bool LoadNames() {
    const std::wstring path = ModuleDirectory() + L"\\OfficialDependencyNames.tsv";
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) {
        Log("cannot open OfficialDependencyNames.tsv");
        return false;
    }

    std::unordered_map<std::string, std::string> names;
    names.reserve(100000);
    std::string line;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty() || line.front() == '#') {
            continue;
        }
        const auto tab = line.find('\t');
        if (tab == std::string::npos || tab == 0 || tab + 1 >= line.size()) {
            Log("invalid mapping line");
            return false;
        }
        names.emplace(line.substr(0, tab), line.substr(tab + 1));
    }
    if (names.size() < 50000) {
        Log("mapping table is unexpectedly small: " + std::to_string(names.size()));
        return false;
    }
    g_names = std::move(names);
    Log("loaded official dependency names: " + std::to_string(g_names.size()));
    return true;
}

void __fastcall HookFallbackName(void* context, const StringRange* id, void* output) noexcept {
    try {
        if (id && id->begin && id->end && id->end >= id->begin) {
            const auto length = static_cast<std::size_t>(id->end - id->begin);
            if (length > 0 && length <= 512) {
                const auto found = g_names.find(std::string(id->begin, length));
                if (found != g_names.end()) {
                    const StringRange translated{
                        found->second.data(), found->second.data() + found->second.size()
                    };
                    g_original(context, &translated, output);
                    return;
                }
            }
        }
    } catch (...) {
        // Preserve the editor's original fallback on any lookup failure.
    }
    g_original(context, id, output);
}

bool BytesEqual(const void* address, const unsigned char* expected, std::size_t size) {
    return std::memcmp(address, expected, size) == 0;
}

void* AllocateNear(const void* target, std::size_t size) {
    SYSTEM_INFO system_info{};
    GetSystemInfo(&system_info);
    const auto granularity = static_cast<std::uintptr_t>(system_info.dwAllocationGranularity);
    const auto target_address = reinterpret_cast<std::uintptr_t>(target);
    const auto distance = static_cast<std::uintptr_t>(INT32_MAX) - granularity;
    const auto minimum = target_address > distance ? target_address - distance : granularity;
    const auto maximum = target_address + distance;

    std::uintptr_t cursor = minimum;
    while (cursor < maximum) {
        MEMORY_BASIC_INFORMATION region{};
        if (!VirtualQuery(reinterpret_cast<void*>(cursor), &region, sizeof(region))) {
            break;
        }
        const auto base = reinterpret_cast<std::uintptr_t>(region.BaseAddress);
        const auto end = base + region.RegionSize;
        if (region.State == MEM_FREE) {
            const auto candidate = (base + granularity - 1) & ~(granularity - 1);
            if (candidate >= minimum && candidate + size <= end && candidate + size < maximum) {
                if (void* memory = VirtualAlloc(
                        reinterpret_cast<void*>(candidate), size,
                        MEM_RESERVE | MEM_COMMIT, PAGE_EXECUTE_READWRITE)) {
                    return memory;
                }
            }
        }
        if (end <= cursor) {
            break;
        }
        cursor = end;
    }
    return nullptr;
}

bool InstallHook() {
    auto* base = reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr));
    if (!base) {
        Log("main module not found");
        return false;
    }
    auto* fallback = base + kFallbackRva;
    auto* call_site = base + kCallSiteRva;
    if (!BytesEqual(fallback, kFallbackSignature, sizeof(kFallbackSignature))) {
        Log("fallback signature mismatch; hook refused");
        return false;
    }
    if (!BytesEqual(call_site, kCallSignature, sizeof(kCallSignature))) {
        Log("call-site signature mismatch; hook refused");
        return false;
    }

    auto* stub = static_cast<unsigned char*>(AllocateNear(call_site, 32));
    if (!stub) {
        Log("cannot allocate a near jump stub");
        return false;
    }
    const unsigned char jump_prefix[] = {0xFF, 0x25, 0x00, 0x00, 0x00, 0x00};
    std::memcpy(stub, jump_prefix, sizeof(jump_prefix));
    const auto hook_address = reinterpret_cast<std::uintptr_t>(&HookFallbackName);
    std::memcpy(stub + sizeof(jump_prefix), &hook_address, sizeof(hook_address));
    FlushInstructionCache(GetCurrentProcess(), stub, 14);

    const auto displacement64 = reinterpret_cast<std::intptr_t>(stub) -
                                reinterpret_cast<std::intptr_t>(call_site + 5);
    if (displacement64 < INT32_MIN || displacement64 > INT32_MAX) {
        VirtualFree(stub, 0, MEM_RELEASE);
        Log("near jump stub is outside rel32 range");
        return false;
    }
    const auto displacement = static_cast<std::int32_t>(displacement64);
    unsigned char patch[5] = {0xE8, 0, 0, 0, 0};
    std::memcpy(patch + 1, &displacement, sizeof(displacement));

    g_original = reinterpret_cast<FallbackName>(fallback);
    DWORD old_protection = 0;
    if (!VirtualProtect(call_site, sizeof(patch), PAGE_EXECUTE_READWRITE, &old_protection)) {
        VirtualFree(stub, 0, MEM_RELEASE);
        Log("VirtualProtect failed at call site");
        return false;
    }
    std::memcpy(call_site, patch, sizeof(patch));
    FlushInstructionCache(GetCurrentProcess(), call_site, sizeof(patch));
    DWORD ignored = 0;
    VirtualProtect(call_site, sizeof(patch), old_protection, &ignored);

    Log("hook installed at SC2Editor_x64.exe+0x404B57");
    return true;
}

DWORD WINAPI Initialize(void*) {
    if (LoadNames()) {
        InstallHook();
    }
    return 0;
}

}  // namespace

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        g_module = instance;
        DisableThreadLibraryCalls(instance);
        if (HANDLE thread = CreateThread(nullptr, 0, Initialize, nullptr, 0, nullptr)) {
            CloseHandle(thread);
        }
    }
    return TRUE;
}

extern "C" __declspec(dllexport) std::size_t SC2L10nGetNameCount() noexcept {
    return g_names.size();
}

extern "C" __declspec(dllexport) const char* SC2L10nGetHookVersion() noexcept {
    return "SC2ED_DPIFIX_L10N_HOOK_VERSION=1.2.0";
}
