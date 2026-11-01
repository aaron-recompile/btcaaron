import inspect, btcaaron
groups = {
 "Keys": ["Key","derive_wif_from_tprv","taproot_descriptor_from_tprv","wif_secret_bytes"],
 "Taproot trees and programs": ["TapTree","TaprootProgram","LeafDescriptor","LEAF_VERSION","LEAF_VERSION_TAPSCRIPT_V2"],
 "Spending": ["SpendBuilder","Transaction"],
 "Scripts and templates": ["Script","RawScript","ord_inscription_script","brc20_mint_json"],
 "Bitcoin Inquisition templates": [n for n in btcaaron.__all__ if n.startswith("inq_")],
 "Signature messages (BIP 341 / BIP 118)": ["compute_sigmsg_preimage","compute_sigmsg_digest","bip118_sighash","apo_pubkey_bytes","SIGHASH_ANYPREVOUT","SIGHASH_ANYPREVOUTANYSCRIPT","SIGHASH_DEFAULT_APO"],
 "PSBT (BIP 174 / 370 / 371)": ["Psbt","PsbtInput","PsbtV2","PsbtV2Input"],
 "Node RPC helpers": ["broadcast_tx_hex","find_utxo_for_address","sats_from_rpc_amount","wallet_change_address","wallet_send_sats"],
 "Errors": ["BtcAaronError","BuildError","BroadcastError","ValidationError"],
 "Legacy v0.1 API": ["WIFKey","BTCAddress","BTCTransaction","wif_to_addresses","quick_transfer","quick_transfer_tprv","taproot_balance_from_tprv","fund_program"],
}
extra_mods = {"btcaaron.templatehash": None}
seen=set(); out=["# btcaaron API reference","",f"Generated from the docstrings of btcaaron {btcaaron.__version__} (`tools/gen_api.py`). Everything listed is importable from the top-level `btcaaron` package unless a module path is shown.",""]
def doc1(o):
    d=inspect.getdoc(o) or ""
    return d.strip().split("\n\n")[0].replace("\n"," ")
def sig(name,o):
    try: return f"{name}{inspect.signature(o)}"
    except (TypeError,ValueError): return name
for g,names in groups.items():
    out += [f"## {g}",""]
    for n in names:
        seen.add(n); o=getattr(btcaaron,n)
        if inspect.isclass(o):
            out += [f"### `class {sig(n,o)}`","",doc1(o) or "_No docstring._",""]
            for mn,m in inspect.getmembers(o):
                if mn.startswith("_") or not (inspect.isfunction(m) or isinstance(inspect.getattr_static(o,mn),(property,classmethod,staticmethod))): continue
                if isinstance(inspect.getattr_static(o,mn),property):
                    out.append(f"- `{mn}` (property): {doc1(inspect.getattr_static(o,mn)) }")
                else:
                    out.append(f"- `{sig(mn,m)}`: {doc1(m)}")
            out.append("")
        elif callable(o):
            out += [f"### `{sig(n,o)}`","",doc1(o) or "_No docstring._",""]
        else:
            out += [f"### `{n}` = `{o!r}`",""]
import btcaaron.templatehash as th
out += ["## BIP 446 template hash (`btcaaron.templatehash`)",""]
for mn,m in inspect.getmembers(th,inspect.isfunction):
    if m.__module__==th.__name__ and not mn.startswith("_"):
        out += [f"### `{sig(mn,m)}`","",doc1(m) or "_No docstring._",""]
missing=[n for n in btcaaron.__all__ if n not in seen and n!="__version__"]
if missing: out += ["## Other",""]+[f"- `{n}`" for n in missing]
open("docs/API.md","w").write("\n".join(out)+"\n")
print("missing:",missing)
