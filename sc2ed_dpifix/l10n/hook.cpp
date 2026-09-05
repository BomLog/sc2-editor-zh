#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>

#include <atomic>
#include <cctype>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <mutex>
#include <string>
#include <unordered_map>
#include <unordered_set>

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
using TreeInsertMessage = LRESULT(WINAPI*)(HWND, UINT, WPARAM, LPARAM);

HMODULE g_module = nullptr;
FallbackName g_original = nullptr;
std::unordered_map<std::string, std::string> g_names;
std::unordered_map<std::string, std::string> g_display_names;
std::unordered_map<std::string, std::string> g_resource_names;
std::unordered_set<std::string> g_preserved_model_ids;
std::wstring g_directory;
ResourceName g_original_resource = nullptr;
thread_local std::string g_resource_translation;
TreeInsertMessage g_original_tree_message = nullptr;
thread_local std::wstring g_tree_translation;

// Diagnostics: count tree insert hook invocations and missed lookups.
std::atomic<int> g_tree_hook_total{0};
std::atomic<int> g_tree_hook_translated{0};
std::atomic<int> g_tree_hook_missed{0};
std::atomic<int> g_tree_hook_empty{0};
std::atomic<int> g_tree_hook_callback{0};  // LPSTR_TEXTCALLBACKW items
std::atomic<int> g_tree_hook_zero_len{0};  // text ptr non-null but empty string
std::atomic<int> g_tree_hook_too_long{0};  // text length > 2048
std::atomic<int> g_tree_hook_conv_fail{0}; // WideToUtf8 returned empty
constexpr int kMaxMissedSamples = 100;
std::string g_missed_samples[kMaxMissedSamples];
std::atomic<int> g_missed_sample_count{0};
std::mutex g_missed_mutex;

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

// Framework layout: the launcher releases the hook package (this DLL plus the
// TSV tables) into a local deploy directory and points the editor process at
// it through SC2ED_DPIFIX_L10N_DATA.  The editor directory itself stays clean
// — it only ever receives resources the editor itself reads.  Without the
// variable (manual LoadLibrary debugging) fall back to the DLL's own folder.
std::wstring DataDirectory() {
    wchar_t buffer[MAX_PATH] = {};
    const DWORD length = GetEnvironmentVariableW(L"SC2ED_DPIFIX_L10N_DATA",
                                                 buffer, MAX_PATH);
    if (length > 0 && length < MAX_PATH) {
        std::wstring result(buffer, length);
        while (!result.empty() && (result.back() == L'\\' || result.back() == L'/')) {
            result.pop_back();
        }
        if (!result.empty()) {
            return result;
        }
    }
    return ModuleDirectory();
}

void Log(const std::string& message) {
    if (g_directory.empty()) {
        g_directory = DataDirectory();
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
    const std::wstring path = DataDirectory() + L"\\OfficialDependencyNames.tsv";
    std::ifstream input(path.c_str(), std::ios::binary);
    if (!input) {
        Log("cannot open OfficialDependencyNames.tsv");
        return false;
    }

    std::unordered_map<std::string, std::string> names;
    std::unordered_map<std::string, std::string> display_names;
    std::unordered_set<std::string> preserved_model_ids;
    names.reserve(100000);
    display_names.reserve(100000);
    preserved_model_ids.reserve(20000);
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
        constexpr char model_prefix[] = "@model:";
        if (source.rfind(model_prefix, 0) == 0) {
            preserved_model_ids.emplace(source.substr(sizeof(model_prefix) - 1));
        } else if (source.rfind(display_prefix, 0) == 0) {
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
    g_preserved_model_ids = std::move(preserved_model_ids);
    Log("loaded official dependency names: " + std::to_string(g_names.size()));
    Log("loaded official dependency display aliases: " +
        std::to_string(g_display_names.size()));
    Log("loaded model ids to preserve: " +
        std::to_string(g_preserved_model_ids.size()));
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

std::string CanonicalDisplayKey(const std::string& key) {
    std::string normalized;
    normalized.reserve(key.size());
    bool pending_space = false;
    for (const unsigned char byte : key) {
        if (byte < 0x80 &&
            (std::isspace(byte) || byte == '(' || byte == ')' || byte == '[' ||
             byte == ']' || byte == '{' || byte == '}')) {
            pending_space = !normalized.empty();
            continue;
        }
        if (pending_space) {
            normalized.push_back(' ');
            pending_space = false;
        }
        normalized.push_back(static_cast<char>(byte));
    }
    while (!normalized.empty() && normalized.back() == ' ') {
        normalized.pop_back();
    }
    return normalized;
}

std::string FlattenHierarchyKey(const std::string& key) {
    std::string flattened = key;
    const char* separators[] = {
        "-", "\xE2\x80\x90", "\xE2\x80\x91", "\xE2\x80\x92",
        "\xE2\x80\x93", "\xE2\x80\x94", "\xE2\x80\x95",
    };
    for (const char* separator : separators) {
        std::size_t position = 0;
        const auto length = std::strlen(separator);
        while ((position = flattened.find(separator, position)) !=
               std::string::npos) {
            flattened.replace(position, length, " ");
            ++position;
        }
    }
    return CanonicalResourceKey(flattened.data(), flattened.size());
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

const std::string* FindExactName(
    const std::unordered_map<std::string, std::string>& names,
    const std::string& key) {
    const auto found = names.find(key);
    return found == names.end() ? nullptr : &found->second;
}

std::string SquashKey(const std::string& key) {
    // Final fallback: composed display texts such as
    // "Spear of Adun Line AOE (Persistent)" turn into the plain catalog id
    // once every space is removed ("spearofadunlineaopersistent"), so a
    // squashed retry reaches the id section of the table without new data.
    // Non-ASCII keys (already-localized Chinese misses) are rejected first
    // so the scan stays allocation-free on the common miss path.
    for (const unsigned char byte : key) {
        if (byte >= 0x80) {
            return std::string();
        }
    }
    std::string squashed;
    squashed.reserve(key.size());
    for (const char byte : key) {
        if (byte != ' ') {
            squashed.push_back(byte);
        }
    }
    return squashed;
}

const std::string* FindTreeName(const std::string& source) {
    const auto key = CanonicalResourceKey(source.data(), source.size());
    const auto display_key = CanonicalDisplayKey(key);
    const auto hierarchy_key = FlattenHierarchyKey(display_key);
    const std::string* candidates[] = {&key, &display_key, &hierarchy_key};

    // Preserve the most-specific alias.  In particular, do not let the
    // annotation fallback turn "Name (Variant) (Final)" into the base Name
    // before the complete, parenthesis-flattened alias has been checked.
    for (const auto* candidate : candidates) {
        if (const auto* found = FindExactName(g_display_names, *candidate)) {
            return found;
        }
    }
    for (const auto* candidate : candidates) {
        if (const auto* found = FindExactName(g_resource_names, *candidate)) {
            return found;
        }
    }

    for (const auto* candidate : candidates) {
        if (const auto* found = FindPresentedName(g_display_names, *candidate)) {
            return found;
        }
    }
    for (const auto* candidate : candidates) {
        if (const auto* found = FindPresentedName(g_resource_names, *candidate)) {
            return found;
        }
    }

    // Squashed-identifier retry (see SquashKey).  Runs only after every
    // whitespace-preserving candidate has missed.
    auto squashed = SquashKey(display_key);
    if (!squashed.empty()) {
        if (const auto* found = FindExactName(g_display_names, squashed)) {
            return found;
        }
        if (const auto* found = FindExactName(g_resource_names, squashed)) {
            return found;
        }
    }
    return nullptr;
}

bool LoadResourceNames() {
    const std::wstring path = DataDirectory() + L"\\OfficialResourceNames.tsv";
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
                if (g_preserved_model_ids.find(source) !=
                    g_preserved_model_ids.end()) {
                    g_original(context, id, output);
                    return;
                }
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

std::string WideToUtf8(const wchar_t* text, std::size_t length) {
    const int required = WideCharToMultiByte(
        CP_UTF8, WC_ERR_INVALID_CHARS, text, static_cast<int>(length),
        nullptr, 0, nullptr, nullptr);
    if (required <= 0) {
        return {};
    }
    std::string result(static_cast<std::size_t>(required), '\0');
    if (WideCharToMultiByte(
            CP_UTF8, WC_ERR_INVALID_CHARS, text, static_cast<int>(length),
            result.data(), required, nullptr, nullptr) != required) {
        return {};
    }
    return result;
}

std::wstring Utf8ToWide(const std::string& text) {
    const int required = MultiByteToWideChar(
        CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()),
        nullptr, 0);
    if (required <= 0) {
        return {};
    }
    std::wstring result(static_cast<std::size_t>(required), L'\0');
    if (MultiByteToWideChar(
            CP_UTF8, MB_ERR_INVALID_CHARS, text.data(), static_cast<int>(text.size()),
            result.data(), required) != required) {
        return {};
    }
    return result;
}

// IAT-wide SendMessageW hook: every tree text operation in the main module
// funnels through this one import slot, including vtable-dispatched calls to
// the tree-control wrapper (sub_141D4BFE0 and friends).  Keep the reject
// path branch-predictor cheap; the atomic counters only tick for the two
// tree messages that actually carry text.
LRESULT WINAPI HookTreeInsertMessage(
    HWND window, UINT message, WPARAM wparam, LPARAM lparam) noexcept {
    if (message != TVM_INSERTITEMW && message != TVM_SETITEMW) {
        return g_original_tree_message(window, message, wparam, lparam);
    }
    try {
        const wchar_t* text = nullptr;
        if (message == TVM_INSERTITEMW && lparam) {
            g_tree_hook_total.fetch_add(1, std::memory_order_relaxed);
            const auto* insertion = reinterpret_cast<const TVINSERTSTRUCTW*>(lparam);
            text = insertion->item.pszText;
        } else if (message == TVM_SETITEMW && lparam) {
            const auto* item = reinterpret_cast<const TVITEMW*>(lparam);
            if (item->mask & TVIF_TEXT) {
                text = item->pszText;
            }
        }
        if (!text) {
            if (message == TVM_INSERTITEMW) {
                g_tree_hook_empty.fetch_add(1, std::memory_order_relaxed);
            }
            return g_original_tree_message(window, message, wparam, lparam);
        }
        if (text == LPSTR_TEXTCALLBACKW) {
            g_tree_hook_callback.fetch_add(1, std::memory_order_relaxed);
            return g_original_tree_message(window, message, wparam, lparam);
        }
        std::size_t length = 0;
        while (length <= 2048 && text[length]) {
            ++length;
        }
        if (length == 0) {
            g_tree_hook_zero_len.fetch_add(1, std::memory_order_relaxed);
            return g_original_tree_message(window, message, wparam, lparam);
        }
        if (length > 2048) {
            g_tree_hook_too_long.fetch_add(1, std::memory_order_relaxed);
            return g_original_tree_message(window, message, wparam, lparam);
        }
        const auto source = WideToUtf8(text, length);
        if (source.empty()) {
            g_tree_hook_conv_fail.fetch_add(1, std::memory_order_relaxed);
            return g_original_tree_message(window, message, wparam, lparam);
        }
        if (const auto* found = FindTreeName(source)) {
            g_tree_hook_translated.fetch_add(1, std::memory_order_relaxed);
            g_tree_translation = Utf8ToWide(*found);
            if (!g_tree_translation.empty()) {
                if (message == TVM_INSERTITEMW) {
                    auto translated =
                        *reinterpret_cast<const TVINSERTSTRUCTW*>(lparam);
                    translated.item.pszText = g_tree_translation.data();
                    translated.item.cchTextMax = static_cast<int>(
                        g_tree_translation.size() + 1);
                    return g_original_tree_message(
                        window, message, wparam,
                        reinterpret_cast<LPARAM>(&translated));
                }
                auto translated = *reinterpret_cast<const TVITEMW*>(lparam);
                translated.pszText = g_tree_translation.data();
                translated.cchTextMax = static_cast<int>(
                    g_tree_translation.size() + 1);
                return g_original_tree_message(
                    window, message, wparam,
                    reinterpret_cast<LPARAM>(&translated));
            }
        } else {
            g_tree_hook_missed.fetch_add(1, std::memory_order_relaxed);
            const int idx = g_missed_sample_count.fetch_add(1,
                std::memory_order_relaxed);
            if (idx < kMaxMissedSamples) {
                std::lock_guard<std::mutex> lock(g_missed_mutex);
                g_missed_samples[idx] = source;
            }
        }
    } catch (...) {
        // Preserve the editor's original tree label on any lookup failure.
    }
    return g_original_tree_message(window, message, wparam, lparam);
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

// Walk the main module's import table and return the IAT slot that the
// loader filled with user32!SendMessageW.  Matching by name keeps this
// independent of binary version and base address; the resolved pointer is
// sanity-checked against GetProcAddress when available.
void** FindSendMessageIatSlot(unsigned char* base) {
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(base);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
        return nullptr;
    }
    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) {
        return nullptr;
    }
    const auto& directory =
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    if (!directory.VirtualAddress) {
        return nullptr;
    }
    const auto expected = reinterpret_cast<std::uintptr_t>(
        GetProcAddress(GetModuleHandleW(L"user32.dll"), "SendMessageW"));
    const auto* imports = reinterpret_cast<const IMAGE_IMPORT_DESCRIPTOR*>(
        base + directory.VirtualAddress);
    for (const auto* descriptor = imports;
         descriptor->OriginalFirstThunk || descriptor->FirstThunk; ++descriptor) {
        const auto* thunk = reinterpret_cast<const IMAGE_THUNK_DATA*>(
            base + (descriptor->OriginalFirstThunk
                        ? descriptor->OriginalFirstThunk
                        : descriptor->FirstThunk));
        auto* iat = reinterpret_cast<IMAGE_THUNK_DATA*>(
            base + descriptor->FirstThunk);
        for (; thunk->u1.AddressOfData; ++thunk, ++iat) {
            if (IMAGE_SNAP_BY_ORDINAL(thunk->u1.Ordinal)) {
                if (expected && iat->u1.Function == expected) {
                    return reinterpret_cast<void**>(&iat->u1.Function);
                }
                continue;
            }
            const auto* by_name = reinterpret_cast<const IMAGE_IMPORT_BY_NAME*>(
                base + thunk->u1.AddressOfData);
            if (std::strcmp(by_name->Name, "SendMessageW") == 0) {
                return reinterpret_cast<void**>(&iat->u1.Function);
            }
        }
    }
    return nullptr;
}

bool InstallTreeInsertHook() {
    if (g_display_names.empty() && g_resource_names.empty()) {
        return false;
    }
    auto* base = reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr));
    if (!base) {
        Log("main module missing for tree insert hook");
        return false;
    }
    auto** slot = FindSendMessageIatSlot(base);
    if (!slot || !*slot) {
        Log("SendMessageW import slot unavailable; tree hook skipped");
        return false;
    }
    g_original_tree_message = reinterpret_cast<TreeInsertMessage>(*slot);

    DWORD old_protection = 0;
    if (!VirtualProtect(slot, sizeof(*slot), PAGE_READWRITE, &old_protection)) {
        g_original_tree_message = nullptr;
        Log("VirtualProtect rejected on SendMessageW import slot");
        return false;
    }
    *slot = reinterpret_cast<void*>(&HookTreeInsertMessage);
    DWORD ignored = 0;
    VirtualProtect(slot, sizeof(*slot), old_protection, &ignored);
    Log("tree localization hook installed on SendMessageW import");
    return true;
}

DWORD WINAPI Initialize(void*) {
    const bool names_loaded = LoadNames();
    if (names_loaded) {
        InstallHook();
    }
    const bool resources_loaded = LoadResourceNames();
    if (resources_loaded) {
        InstallResourceHook();
    }
    if (names_loaded || resources_loaded) {
        InstallTreeInsertHook();
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
    } else if (reason == DLL_PROCESS_DETACH) {
        const int total = g_tree_hook_total.load(std::memory_order_relaxed);
        const int translated = g_tree_hook_translated.load(std::memory_order_relaxed);
        const int missed = g_tree_hook_missed.load(std::memory_order_relaxed);
        const int empty = g_tree_hook_empty.load(std::memory_order_relaxed);
        const int callback = g_tree_hook_callback.load(std::memory_order_relaxed);
        const int zero_len = g_tree_hook_zero_len.load(std::memory_order_relaxed);
        const int too_long = g_tree_hook_too_long.load(std::memory_order_relaxed);
        const int conv_fail = g_tree_hook_conv_fail.load(std::memory_order_relaxed);
        Log("=== Tree Hook Diagnostics ===");
        Log("total=" + std::to_string(total) +
            " translated=" + std::to_string(translated) +
            " missed=" + std::to_string(missed) +
            " empty=" + std::to_string(empty));
        Log("callback=" + std::to_string(callback) +
            " zero_len=" + std::to_string(zero_len) +
            " too_long=" + std::to_string(too_long) +
            " conv_fail=" + std::to_string(conv_fail));
        const int sample_count = g_missed_sample_count.load(std::memory_order_relaxed);
        const int clamped = sample_count < kMaxMissedSamples ? sample_count : kMaxMissedSamples;
        for (int i = 0; i < clamped; ++i) {
            Log("MISSED[" + std::to_string(i) + "]: " + g_missed_samples[i]);
        }
        if (sample_count > kMaxMissedSamples) {
            Log("... and " + std::to_string(sample_count - kMaxMissedSamples) + " more missed samples");
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

extern "C" __declspec(dllexport) std::size_t SC2L10nGetPreservedModelIdCount() noexcept {
    return g_preserved_model_ids.size();
}

extern "C" __declspec(dllexport) const char* SC2L10nGetTreeInsertHookMarker() noexcept {
    return "SC2ED_DPIFIX_TREE_INSERT_HOOK=1";
}

extern "C" __declspec(dllexport) const char* SC2L10nGetHookVersion() noexcept {
    return "SC2ED_DPIFIX_L10N_HOOK_VERSION=1.5.0";
}

// Plain static buffer: diagnostics may be requested from a transient remote
// thread (Cheat Engine), whose thread_local storage dies with the thread and
// would leave the returned pointer dangling.
static std::string g_diagnostics_buffer;

extern "C" __declspec(dllexport) const char* SC2L10nGetDiagnostics() noexcept {
    try {
        const int total = g_tree_hook_total.load(std::memory_order_relaxed);
        const int translated = g_tree_hook_translated.load(std::memory_order_relaxed);
        const int missed = g_tree_hook_missed.load(std::memory_order_relaxed);
        const int empty = g_tree_hook_empty.load(std::memory_order_relaxed);
        const int callback = g_tree_hook_callback.load(std::memory_order_relaxed);
        const int zero_len = g_tree_hook_zero_len.load(std::memory_order_relaxed);
        const int too_long = g_tree_hook_too_long.load(std::memory_order_relaxed);
        const int conv_fail = g_tree_hook_conv_fail.load(std::memory_order_relaxed);
        std::string result = "total=" + std::to_string(total) +
            " translated=" + std::to_string(translated) +
            " missed=" + std::to_string(missed) +
            " empty=" + std::to_string(empty) + "\n";
        result += "callback=" + std::to_string(callback) +
            " zero_len=" + std::to_string(zero_len) +
            " too_long=" + std::to_string(too_long) +
            " conv_fail=" + std::to_string(conv_fail) + "\n";
        const int sample_count = g_missed_sample_count.load(std::memory_order_relaxed);
        const int clamped = sample_count < kMaxMissedSamples ? sample_count : kMaxMissedSamples;
        for (int i = 0; i < clamped; ++i) {
            result += "MISSED[" + std::to_string(i) + "]: " + g_missed_samples[i] + "\n";
        }
        if (sample_count > kMaxMissedSamples) {
            result += "... and " + std::to_string(sample_count - kMaxMissedSamples) + " more\n";
        }
        g_diagnostics_buffer = std::move(result);
        return g_diagnostics_buffer.c_str();
    } catch (...) {
        return "error";
    }
}
