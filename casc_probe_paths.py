import _casc

inst = _casc.open(r"D:\StarCraft II")

candidates = [
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\gamestrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\objectstrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\conversationstrings.txt",
    r"mods\core.sc2mod\zhcn.sc2data\localizeddata\errors.txt",
    r"campaigns\liberty.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\swarm.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\void.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\libertystory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\swarmstory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\voidstory.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\novacampaign.sc2campaign\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\gamestrings.txt",
    r"campaigns\swarmstoryutil.sc2mod\zhcn.sc2data\localizeddata\objectstrings.txt",
    r"mods\starcoop.sc2mod\zhcn.sc2data\localizeddata\triggerstrings.txt",
    r"mods\starcoop.sc2mod\zhcn.sc2data\localizeddata\gamestrings.txt",
    r"mods\starcoop.sc2mod\zhcn.sc2data\localizeddata\objectstrings.txt",
]

print("=== direct probe ===")
for name in candidates:
    try:
        r = _casc.open_file(inst, name)
        ok = r[0] if isinstance(r, tuple) else r
        print(("  EXISTS " if ok else "  miss   "), name)
    except Exception as e:
        print("  ERR    ", name, type(e).__name__, e)

# try find_next_file with mask
print("=== find_next_file(inst, mask) ===")
try:
    r = _casc.find_next_file(inst, "*gamestrings.txt")
    print("  ->", repr(r)[:200])
except Exception as e:
    print("  ERR", type(e).__name__, e)

_casc.close(inst)
