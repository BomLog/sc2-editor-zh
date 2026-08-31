#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <cctype>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <unordered_map>

namespace {

constexpr std::uintptr_t kFallbackRva = 0x297B70;
constexpr std::uintptr_t kCallSiteRva = 0x404B57;
constexpr std::uintptr_t kResourceRva = 0x1D4BFE0;
constexpr std::uintptr_t kResourceCallSiteRva = 0x1D4A8C8;
constexpr unsigned char kFallbackSignature[] = {
    0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x40,
};
constexpr unsigned char kCallSignature[] = {0xE8, 0x14, 0x30, 0xE9, 0xFF};
constexpr unsigned char kResourceCallSignature[] = {0xE8, 0x13, 0x17, 0x00, 0x00};

struct StringRange {
    const char* begin;
    const char* end;
};

using FallbackName = void(__fastcall*)(void*, const StringRange*, void*);
using ResourceName = std::int64_t(__fastcall*)(void*, std::uintptr_t, StringRange*);

HMODULE g_module = nullptr;
FallbackName g_original = nullptr;
std::unordered_map<std::string, std::string> g_names;
std::unordered_map<std::string, std::string> g_display_names;
std::unordered_map<std::string, std::string> g_resource_names;
std::wstring g_directory;
ResourceName g_original_resource = nullptr;
thread_local std::string g_resource_translation;

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
    std::unordered_map<std::string, std::string> display_names;
    names.reserve(100000);
    display_names.reserve(100000);
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
        const auto source = line.substr(0, tab);
        constexpr char display_prefix[] = "@display:";
        if (source.rfind(display_prefix, 0) == 0) {
            display_names.emplace(
                source.substr(sizeof(display_prefix) - 1), line.substr(tab + 1)
            );
        } else {
            names.emplace(source, line.substr(tab + 1));
        }
    }
    if (names.size() < 50000) {
        Log("mapping table is unexpectedly small: " + std::to_string(names.size()));
        return false;
    }
    g_names = std::move(names);
    g_display_names = std::move(display_names);
    Log("loaded official dependency names: " + std::to_string(g_names.size()));
    Log("loaded official dependency display aliases: " +
        std::to_string(g_display_names.size()));
    return true;
}

std::string CanonicalResourceKey(const char* begin, std::size_t length) {
    std::string key;
    key.reserve(length);
    bool pending_space = false;
    for (std::size_t index = 0; index < length; ++index) {
        const unsigned char byte = static_cast<unsigned char>(begin[index]);
        // Normalize the UTF-8 non-breaking and ideographic spaces that are
        // emitted by some localized resource-tree views.  The table itself
        // deliberately stays ASCII-space separated so it remains portable.
        if (byte == 0xC2 && index + 1 < length &&
            static_cast<unsigned char>(begin[index + 1]) == 0xA0) {
            pending_space = !key.empty();
            ++index;
            continue;
        }
        if (byte == 0xE3 && index + 2 < length &&
            static_cast<unsigned char>(begin[index + 1]) == 0x80 &&
            static_cast<unsigned char>(begin[index + 2]) == 0x80) {
            pending_space = !key.empty();
            index += 2;
            continue;
        }
        if (byte < 0x80 && std::isspace(byte)) {
            pending_space = !key.empty();
            continue;
        }
        if (pending_space) {
            key.push_back(' ');
            pending_space = false;
        }
        key.push_back(byte < 0x80 ? static_cast<char>(std::tolower(byte))
                                  : static_cast<char>(byte));
    }
    while (!key.empty() && key.back() == ' ') {
        key.pop_back();
    }
    return key;
}

const std::string* FindPresentedName(
    const std::unordered_map<std::string, std::string>& names,
    const std::string& key) {
    auto exact = [&](const std::string& candidate) -> const std::string* {
        const auto found = names.find(candidate);
        return found == names.end() ? nullptr : &found->second;
    };
    if (const auto* found = exact(key)) {
        return found;
    }

    // A path occasionally reaches this callback instead of its basename.
    // Retry the final slash-delimited component before applying presentation
    // suffix rules.
    const auto slash = key.find_last_of("\\/");
    if (slash != std::string::npos && slash + 1 < key.size()) {
        if (const auto* found = exact(key.substr(slash + 1))) {
            return found;
        }
    }

    // Some resource-browser rows append their catalog group in parentheses,
    // e.g. ``(Impact FX)``.  The generated table is keyed by the leaf model
    // name, so retry without that presentation-only suffix.  Handle both
    // spaced and directly attached parentheses and strip nested annotations.
    std::string without_annotation = key;
    for (;;) {
        const auto parenthesis = without_annotation.rfind('(');
        if (parenthesis == std::string::npos) {
            break;
        }
        without_annotation.resize(parenthesis);
        while (!without_annotation.empty() && without_annotation.back() == ' ') {
            without_annotation.pop_back();
        }
        if (const auto* found = exact(without_annotation)) {
            return found;
        }
    }

    // Hierarchical resource views use a dash between a category and the
    // leaf.  Accept all common Unicode dash encodings, with or without spaces,
    // and the ASCII hyphen variant used by older editor builds.  Search from
    // left to right so a category containing a dash can still fall through to
    // the deepest matching leaf.
    const char* separators[] = {
        "-", "\xE2\x80\x90", "\xE2\x80\x91", "\xE2\x80\x92",
        "\xE2\x80\x93", "\xE2\x80\x94", "\xE2\x80\x95",
    };
    for (const char* separator : separators) {
        std::size_t split = 0;
        while ((split = key.find(separator, split)) != std::string::npos) {
            auto leaf = key.substr(split + std::strlen(separator));
            while (!leaf.empty() && leaf.front() == ' ') {
                leaf.erase(leaf.begin());
            }
            if (const auto* found = exact(leaf)) {
                return found;
            }
            ++split;
        }
    }

    // Colon and slash are also used as hierarchy separators by a few debug
    // builds.  They are not generated aliases themselves, so only use the
    // suffix as a fallback after exact matching has failed.
    for (const char* separator : {":", ">", "/", "\\"}) {
        const auto split = key.rfind(separator);
        if (split != std::string::npos && split + 1 < key.size()) {
            auto leaf = key.substr(split + 1);
            while (!leaf.empty() && leaf.front() == ' ') {
                leaf.erase(leaf.begin());
            }
            if (const auto* found = exact(leaf)) {
                return found;
            }
        }
    }

    if (without_annotation != key) {
        // Apply hierarchy stripping to the annotation-free form as well.
        for (const char* separator : separators) {
            std::size_t split = 0;
            while ((split = without_annotation.find(separator, split)) !=
                   std::string::npos) {
                auto leaf = without_annotation.substr(split + std::strlen(separator));
                while (!leaf.empty() && leaf.front() == ' ') {
                    leaf.erase(leaf.begin());
                }
                if (const auto* found = exact(leaf)) {
                    return found;
                }
                ++split;
            }
        }
    }

    // A few rows append a localized annotation directly to an ASCII model
    // id (for example ``ZeratulShadowCleave攻击(未命名)``).  Preserve the
    // leading ASCII token and use it as a final, deliberately conservative
    // lookup candidate.
    std::size_t ascii_end = 0;
    while (ascii_end < key.size() &&
           static_cast<unsigned char>(key[ascii_end]) < 0x80) {
        ++ascii_end;
    }
    if (ascii_end > 0 && ascii_end < key.size()) {
        const auto prefix = names.find(key.substr(0, ascii_end));
        if (prefix != names.end()) {
            return &prefix->second;
        }
    }
    return nullptr;
}

bool LoadResourceNames() {
    const std::wstring path = ModuleDirectory() + L"\\OfficialResourceNames.tsv";
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) {
        Log("cannot open OfficialResourceNames.tsv; resource hook disabled");
        return false;
    }

    std::unordered_map<std::string, std::string> names;
    names.reserve(40000);
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
            Log("invalid resource mapping line");
            return false;
        }
        const auto key = CanonicalResourceKey(line.data(), tab);
        if (key.empty()) {
            Log("empty resource mapping key");
            return false;
        }
        names.emplace(key, line.substr(tab + 1));
    }
    if (names.size() < 100) {
        Log("resource mapping table is unexpectedly small: " + std::to_string(names.size()));
        return false;
    }
    g_resource_names = std::move(names);
    Log("loaded official resource names: " + std::to_string(g_resource_names.size()));
    return true;
}

void __fastcall HookFallbackName(void* context, const StringRange* id, void* output) noexcept {
    try {
        if (id && id->begin && id->end && id->end >= id->begin) {
            const auto length = static_cast<std::size_t>(id->end - id->begin);
            if (length > 0 && length <= 512) {
                const std::string source(id->begin, length);
                const auto found = g_names.find(source);
                if (found != g_names.end()) {
                    const StringRange translated{
                        found->second.data(), found->second.data() + found->second.size()
                    };
                    g_original(context, &translated, output);
                    return;
                }
                const auto key = CanonicalResourceKey(source.data(), source.size());
                if (const auto* displayed = FindPresentedName(g_display_names, key)) {
                    const StringRange translated{
                        displayed->data(), displayed->data() + displayed->size()
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

std::int64_t __fastcall HookResourceName(
    void* context, std::uintptr_t item, StringRange* input) noexcept {
    try {
        if (input && input->begin && input->end && input->end >= input->begin) {
            const auto length = static_cast<std::size_t>(input->end - input->begin);
            if (length > 0 && length <= 2048) {
                const auto key = CanonicalResourceKey(input->begin, length);
                if (const auto* found = FindPresentedName(g_resource_names, key)) {
                    g_resource_translation = *found;
                    StringRange translated{
                        g_resource_translation.data(),
                        g_resource_translation.data() + g_resource_translation.size(),
                    };
                    return g_original_resource(context, item, &translated);
                }
            }
        }
    } catch (...) {
        // Preserve the editor's original resource rendering on lookup failure.
    }
    return g_original_resource(context, item, input);
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

bool InstallResourceHook() {
    if (g_resource_names.empty()) {
        return false;
    }
    auto* base = reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr));
    if (!base) {
        Log("main module not found for resource hook");
        return false;
    }
    auto* resource = base + kResourceRva;
    auto* call_site = base + kResourceCallSiteRva;
    if (!BytesEqual(call_site, kResourceCallSignature, sizeof(kResourceCallSignature))) {
        Log("resource call-site signature mismatch; hook refused");
        return false;
    }

    auto* stub = static_cast<unsigned char*>(AllocateNear(call_site, 32));
    if (!stub) {
        Log("cannot allocate a near jump stub for resource hook");
        return false;
    }
    const unsigned char jump_prefix[] = {0xFF, 0x25, 0x00, 0x00, 0x00, 0x00};
    std::memcpy(stub, jump_prefix, sizeof(jump_prefix));
    const auto hook_address = reinterpret_cast<std::uintptr_t>(&HookResourceName);
    std::memcpy(stub + sizeof(jump_prefix), &hook_address, sizeof(hook_address));
    FlushInstructionCache(GetCurrentProcess(), stub, 14);

    const auto displacement64 = reinterpret_cast<std::intptr_t>(stub) -
                                reinterpret_cast<std::intptr_t>(call_site + 5);
    if (displacement64 < INT32_MIN || displacement64 > INT32_MAX) {
        VirtualFree(stub, 0, MEM_RELEASE);
        Log("resource near jump stub is outside rel32 range");
        return false;
    }
    const auto displacement = static_cast<std::int32_t>(displacement64);
    unsigned char patch[5] = {0xE8, 0, 0, 0, 0};
    std::memcpy(patch + 1, &displacement, sizeof(displacement));

    g_original_resource = reinterpret_cast<ResourceName>(resource);
    DWORD old_protection = 0;
    if (!VirtualProtect(call_site, sizeof(patch), PAGE_EXECUTE_READWRITE, &old_protection)) {
        VirtualFree(stub, 0, MEM_RELEASE);
        Log("VirtualProtect failed at resource call site");
        return false;
    }
    std::memcpy(call_site, patch, sizeof(patch));
    FlushInstructionCache(GetCurrentProcess(), call_site, sizeof(patch));
    DWORD ignored = 0;
    VirtualProtect(call_site, sizeof(patch), old_protection, &ignored);
    Log("resource basename hook installed at SC2Editor_x64.exe+0x1D4A8C8");
    return true;
}

DWORD WINAPI Initialize(void*) {
    if (LoadNames()) {
        InstallHook();
    }
    if (LoadResourceNames()) {
        InstallResourceHook();
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

extern "C" __declspec(dllexport) std::size_t SC2L10nGetDisplayAliasCount() noexcept {
    return g_display_names.size();
}

extern "C" __declspec(dllexport) std::size_t SC2L10nGetResourceNameCount() noexcept {
    return g_resource_names.size();
}

extern "C" __declspec(dllexport) const char* SC2L10nGetHookVersion() noexcept {
    return "SC2ED_DPIFIX_L10N_HOOK_VERSION=1.3.1";
}
