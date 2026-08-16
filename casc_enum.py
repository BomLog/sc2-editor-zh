import _casc, json

inst = _casc.open(r"D:\StarCraft II")

def enum(mask, out):
    h = _casc.find_first_file(inst, mask)
    hh = h
    while hh is not None and hh != 0:
        ptr, meta = hh
        out.append(meta)
        hh = _casc.find_next_file(ptr)
    try:
        if isinstance(h, tuple):
            _casc.find_close(h[0])
        else:
            _casc.find_close(h)
    except Exception:
        pass

results = []
# all zhcn localizeddata txt (game data + assets)
enum("*zhcn*localizeddata*.txt", results)

print("total zhcn localizeddata txt files:", len(results))
# classify
str_files = []
for m in results:
    fn = m["filename"]
    low = fn.lower()
    if any(k in low for k in ["gamestrings.txt", "objectstrings.txt", "triggerstrings.txt",
                              "conversationstrings.txt", "editorstrings.txt", "errors.txt",
                              "editorcatalogstrings", "editorcategorystrings"]):
        str_files.append(m)

print("=== string files (%d) ===" % len(str_files))
for m in str_files:
    print("  ", m["filename"], m["file_size"])

json.dump(results, open(r"E:\Code\sc2\Work\casc_zhcn_txt_files.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("wrote casc_zhcn_txt_files.json")

_casc.close(inst)
