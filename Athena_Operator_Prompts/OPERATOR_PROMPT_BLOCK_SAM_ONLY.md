# OPERATOR_PROMPT_BLOCK_SAM_ONLY.md

## 🟩 OPERATOR PROMPT BLOCK — SAM-ONLY BENCHMARK (GT PROMPTS)

```
OPERATOR PROMPT BLOCK — SAM-ONLY BENCHMARK (6 CONFIGS)
Task Title:
Run SAM-only benchmark on AerialFuseCV using ground-truth prompts.

Task Steps:
1. Open and verify the following scripts:
   - src/benchmarks/sam_benchmark.py
   - src/utils/metrics.py
   - src/utils/prompt_gen.py
   - src/datasets/aerial_fuse_cv_dataloader.py

2. Ensure sam_benchmark.py supports:
   - SAM models: vit_h, vit_l, vit_b
   - Prompt types: "box", "point"
   - Input OBBs from GT annotations
   - Output folder: results/sam_only/<model>/<prompt>/

3. For each SAM model:
   a. Run:
      python -m src.benchmarks.sam_benchmark --sam vit_h --prompt box
      python -m src.benchmarks.sam_benchmark --sam vit_h --prompt point

      python -m src.benchmarks.sam_benchmark --sam vit_l --prompt box
      python -m src.benchmarks.sam_benchmark --sam vit_l --prompt point

      python -m src.benchmarks.sam_benchmark --sam vit_b --prompt box
      python -m src.benchmarks.sam_benchmark --sam vit_b --prompt point

4. Store outputs:
   - metrics.json in each config folder
   - metrics_summary.csv in results/sam_only/
   - qualitative_examples/ with 5 good + 5 bad predictions per config

5. After completion:
   - Summarize runtime stats
   - Print a short table of results (IoU, DICE, Boundary F1)
   - Upload all results to results/sam_only/
```
