# Model local-runnability ladder (can it run on THIS box?)

Purpose: when a post/model claims "you can run it locally", produce an **objective** yes/no
instead of guessing from the model card. Every step is a curl + a comparison. Verified end-to-end
on the OUI-1 case (Sep 2026).

Our ceiling to compare against (re-measure if it matters): **2 vCPU, 11,927MB RAM
(~4.8GB available, 3GB swap already in use), NO GPU, ~94GB free disk**, Ollama present
(qwen2.5:7b/3b, llama3.2:3b, llava:7b, bge-m3, nomic-embed-text). Re-verify cheaply with:

```bash
echo CPU:$(nproc) ; free -m | awk 'NR==2{print "RAM_MB total="$2" used="$3" avail="$7}'
echo SWAP used=$(free -m | awk 'NR==3{print $3}') ; df -h / | tail -1
nvidia-smi -L 2>/dev/null || echo "GPU:none" ; ollama list | head
```

## Ladder (run top to bottom, stop at the first hard no)

1. **HF model card + arch**
   ```bash
   curl -s https://huggingface.co/api/models/{org}/{name}      # license, downloads, likes, siblings, tags
   curl -s https://huggingface.co/api/models/{org}/{name}/resolve/main/config.json | head -60
   ```
   Read `architectures` (e.g. `DiffusionGemmaForBlockDiffusion`) and the sibling SIZES
   (`?blobs=true` or the `siblings` list) → bf16 weight size = the VRAM floor.
   Empty `inferenceProviderMapping` in the card response = **no HF serverless path**, so
   "just call it on HF" is off the table.

2. **Is the architecture SUPPORTED by a local runtime?** — the step everyone skips.
   ```bash
   curl -s "https://api.github.com/search/issues?q=repo:ggml-org/llama.cpp+{arch_keyword}&per_page=5" \
     | python3 -c 'import sys,json;[print(i["number"],i["state"],i["title"]) for i in json.load(sys.stdin)["items"]]'
   curl -s -o /dev/null -w "%{http_code}\n" https://registry.ollama.ai/v2/library/{model}/manifests/latest
   ```
   - llama.cpp issue/PR **OPEN** for the arch → mainline cannot run it, regardless of GGUFs on HF.
   - Ollama registry manifest **404** → no `ollama pull` path (a search-result page on ollama.com
     is NOT a manifest; check the registry API, not the search UI).
   - `configuration_*.json` present in the HF repo (for `library_name: transformers`) → the
     transformers path may exist, but that means **GPU only**, not this box.

3. **Community quants — size, not existence**
   ```bash
   curl -s "https://huggingface.co/api/models?search={model}-GGUF&limit=20" | python3 -c 'import sys,json;[print(m["id"]) for m in json.load(sys.stdin)]'
   curl -s https://huggingface.co/api/models/{quant_repo} | python3 -c 'import sys,json;d=json.load(sys.stdin);[print(s["rfilename"], s.get("size")) for s in d.get("siblings",[])]'
   ```
   Compare the **smallest** quant against available RAM (and VRAM): if the smallest is bigger than
   RAM, the only paths are mmap+disk (unusably slow at 2 vCPU) or a rented GPU.

4. **Verdict line to write**: "❌ not on our box today — <hard blocker: no GPU / smallest quant X > RAM / arch support still open in llama.cpp>. 👀 watchlist trigger = <PR merge OR Ollama manifest OR we rent a GPU>." Add the cloud option **with its data clause** (free tiers often train on your prompts → client data disqualified) and an estimated latency/VRAM for the rented-GPU variant if the tech is otherwise valuable.

## OUI-1 case study (worked example, Sep 2026)

- `thesysdev/OUI-1`, Apache-2.0, base `google/diffusiongemma-26B-A4B-it`, arch
  `DiffusionGemmaForBlockDiffusion`, 256-token block diffusion, 16k ctx, bf16 ≈ 51.6GB,
  1,339 downloads / 91 likes at check time. Scores 71.7% (132/184) on `thesysdev/generative-ui-bench`
  vs base 13.0% (24/184); ~1s per screen on a single GPU.
- Runnability result: **not runnable here** — no GPU; smallest community quant Q3_K_M ≈ 13.3GB
  > 11.9GB RAM (Q4_K_M 16.8GB, Q8 26.9GB); llama.cpp "Add diffusion-gemma block-diffusion support"
  issue + the DiffusionGemma issue both **OPEN**; Ollama registry manifest **404**; HF
  `inferenceProviderMapping` empty; transformers config exists → GPU-only (FP8 ≈ 26GB VRAM,
  i.e. RTX-5090 class).
- Reliability numbers travel with the tech, not the model: even the benchmark best pairing was
  99.5%, and general-model + validation reached 92.9% — so any UI/JSON generation path needs a
  **validate + repair gate** (errors-as-data, exit 0) rather than trusting the model.
- Lesson: the *language/runtime* (MIT DSL + React/IIFE renderer) was adoptable with zero GPU while
  the *model* was not — when a post bundles both, split the verdict into the two halves.
