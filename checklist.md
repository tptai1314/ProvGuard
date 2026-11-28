# ProvGuard — Track B (Full AOSP) ROADMAP & Checklist

> **Mục tiêu:** Chạy **100% Full Paper trên Track B (OS-enforced TCB)** với Android 15 (`android-15.0.0_r14`) đã patch `ProvGuardManagerService`, `SurfaceFlinger`, `InputDispatcher`, `SystemUI`, và `SELinux`.
> **Trạng thái hiện tại:** Đã hoàn thành **Phase 0** (`79 passed, 6 skipped`). Các bảng/biểu đồ trong `sections/experiments.tex` hiện đang là placeholder.

---

## 🗺️ ROADMAP Track B (6 Phases)

```text
[Phase 0: Local Pre-check (Windows)]
         │
         ▼
[Phase 1: Linux/EC2 Host Setup] ──► (Có /dev/kvm: Cuttlefish | Không /dev/kvm: AVD emu_img_zip)
         │
         ▼
[Phase 2: Sync AOSP android-15.0.0_r14 & Apply Hooks]
         │
         ▼
[Phase 3: Build & Boot AOSP Image + Verify `"aosp_tcb":true`]
         │
         ▼
[Phase 4: Provision 5 External Datasets + Khởi chạy vLLM / Model]
         │
         ▼
[Phase 5: Chạy Full Paper Matrix (Table 8 + Table 6 + RQ4 Sweep)]
         │
         ▼
[Phase 6: Sinh Bảng/Figures + Kiểm tra Provenance + Build main.pdf]
```

### Yêu cầu phần cứng & môi trường cho Track B
- **Build AOSP:** Ubuntu 22.04 / 24.04, tối thiểu **64 GB RAM**, **400 GB SSD** (ví dụ AWS `c7i.8xlarge` hoặc `r6i.4xlarge`).
- **Chạy Cuttlefish trực tiếp trên cloud:** Cần instance hỗ trợ `/dev/kvm` (ví dụ `c7i.metal-24xl` / `i3en.metal` hoặc máy trạm Linux bật KVM). *Nếu thuê VM không có `/dev/kvm`, có thể build target `emulator` (`m emu_img_zip`) rồi kéo AVD zip về máy có KVM / Windows Emulator.*
- **Chạy vLLM cho 4 agents:** GPU Linux (A10G / L4 / A100 tùy model, mặc định script dùng `ByteDance-Seed/UI-TARS-7B-DPO`).

---

## ✅ CHECKLIST CHI TIẾT (TRACK B)

### Phase 0: Pre-check nhanh trên Windows (✅ Hoàn thành)
- [x] **0.1. Tạo venv & kiểm tra core Python + AOSP bridge host tests**
  ```powershell
  cd ProvGuard
  python -m venv .venv
  .\.venv\Scripts\activate
  pip install -e ".[dev]"
  pytest -q
  pytest tests/test_aosp_bridge.py -q
  ```
  - *Kết quả thực tế:* **79 passed, 6 skipped** trong 10.79s.
    - 1 skip ở `tests/test_aosp_bridge.py:180` (`android.jar` / `aidl` chưa có trong `ANDROID_HOME`).
    - 5 skip ở `tests/test_external_suites.py` (5 external datasets chưa tải, sẽ tải ở Phase 4).

---

### Phase 1: Provision Linux / EC2 Build Host (✅ Hoàn thành trên `52.87.64.180`)
- [x] **1.1. Cài đặt gói build AOSP, `repo`, `openjdk-17-jdk`, `adb`, `qemu-kvm`**
  ```bash
  bash aosp/scripts/ec2_setup.sh
  ```
  - *Kết quả:* Đã chạy xong trên `52.87.64.180` (Ubuntu 24.04.5, 16 vCPU, 62 GiB RAM, 482 GB disk trống), kèm `tmux 3.4` và `NVIDIA Driver 595.91.07` (GPU **NVIDIA A10G 24 GB**, `nvidia-smi` đã nhận).
- [ ] **1.2. Kiểm tra `/dev/kvm` & Cuttlefish host packages**
  - *Ghi chú thực tế:* EC2 `52.87.64.180` là `g5.4xlarge` nên không có `/dev/kvm`; sẽ build AOSP target `emulator` (`m emu_img_zip`) hoặc chạy đánh giá trên GPU A10G.

---

### Phase 2: Sync AOSP `android-15.0.0_r14` & Apply ProvGuard Patches (✅ Hoàn thành)
- [x] **2.1. Đồng bộ mã nguồn AOSP & tự động kiểm tra/áp dụng hooks + overlay**
  ```bash
  bash aosp/scripts/sync_and_apply.sh "$HOME/aosp-provguard"
  ```
  - *Kết quả:* `Phase 2 OK!` (đã sync xong `android-15.0.0_r14` và áp dụng thành công ProvGuard overlay + hooks).
- [ ] **2.2. Ghi nhận Provenance của AOSP**
  - Lưu lại AOSP tag (`android-15.0.0_r14`), commit hash/manifest và hash các file patch theo yêu cầu trong `ProvGuard/docs/reproducibility.md`.

---

### Phase 3: Build & Boot AOSP Image + Verify OS-level TCB
- [ ] **3.1. Compile AOSP**
  - **Nhánh 1 (Máy có `/dev/kvm` — Cuttlefish):**
    ```bash
    bash aosp/scripts/build_cuttlefish.sh "$HOME/aosp-provguard" cuttlefish
    ```
  - **Nhánh 2 (VM không có `/dev/kvm` — Build AVD zip):**
    ```bash
    bash aosp/scripts/build_cuttlefish.sh "$HOME/aosp-provguard" emulator
    # Sau đó copy out/target/product/emu64x/sdk-repo-linux-system-images-*.zip sang máy có KVM/Emulator
    ```
- [ ] **3.2. Boot Cuttlefish & xác nhận `ProvGuardManagerService` đang chạy trong `system_server`**
  ```bash
  bash aosp/scripts/launch_cuttlefish.sh "$HOME/aosp-provguard"
  ```
  - *Expected output bắt buộc:*
    - `adb shell cmd provguard status` trả về JSON có `"aosp_tcb":true`.
    - In ra dòng `SUCCESS: ProvGuard AOSP TCB is live on Cuttlefish!`.
- [ ] **3.3. Smoke-test Live AttackKit trên OS đã patch**
  - Build & cài 3 APK từ `android/attackkit/` (`hidden`, `overlay`, `notif`) lên Cuttlefish/Emulator.
  - Chạy `python ProvGuard/scripts/run_live_emulator.py --scenario hidden --agent ui-tars ...` và kiểm tra `adb shell cmd provguard telemetry` ghi nhận lượt đánh giá của Gate & Binder.

---

### Phase 4: Provision External Benchmarks & Khởi chạy Model Server
- [ ] **4.1. Cài Python package & tải 5 External Benchmarks**
  ```bash
  bash aosp/scripts/provision_datasets_ec2.sh
  ```
  - *Kiểm tra:* Đủ 5 bộ trong `datasets_external/`:
    - `AgentHazard` (đã giải nén `data/data/static` từ `exp.7z`)
    - `Ghost-EI`
    - `Not-An-A11y`
    - `android_world`
    - `Android-Lab`
- [ ] **4.2. Khởi chạy vLLM Server (hoặc cấu hình API ngoài)**
  - Ví dụ phục vụ `ByteDance-Seed/UI-TARS-7B-DPO` trên cổng `8000`:
    ```bash
    vllm serve ByteDance-Seed/UI-TARS-7B-DPO --port 8000
    ```
  - *(Nếu dùng OpenAI/Gemini API thay cho vLLM, export `PROVIDER`, `VLLM_BASE_URL`, `VLLM_API_KEY`, `VLLM_MODEL` tương ứng trước khi chạy Phase 5.)*

---

### Phase 5: Chạy Full Paper Evaluation Matrix (RQ1–RQ7)
Chạy script tổng hợp [run_ec2_paper_eval.sh](file:///d:/NCKH/MobileSYS/New%20folder/ProvGuard/aosp/scripts/run_ec2_paper_eval.sh):
```bash
VLLM_BASE_URL=http://localhost:8000/v1 \
VLLM_MODEL=ByteDance-Seed/UI-TARS-7B-DPO \
REPS=5 \
OUT_ROOT=results_paper_ec2 \
  bash aosp/scripts/run_ec2_paper_eval.sh
```
Script này sẽ lần lượt thực thi và khóa manifest (`--freeze`) cho:
- [ ] **5.1. Table 8 (RQ1, RQ2, RQ6, RQ7) — 10 cấu hình × 4 agents × 5 reps**
  - Configs: `B0, B1, B2, B3, B4, labels, gate, binder, no_perc, full`
  - Agents: `droidrun`, `ui-tars`, `open-autoglm`, `mobile-agent-v3`
  - Output: `results_paper_ec2/table8_<agent>/trials.jsonl`
- [ ] **5.2. Table 6 & RQ5 — 6 External & Adaptive Suites × 4 agents**
  - `AgentHazard` (G1 default & strict third-party), `GhostEI-Bench`, `Not-An-A11y`, `Adaptive`, `AndroidWorld`, `AndroidLab`
  - Output: `results_paper_ec2/external_<agent>/`
- [ ] **5.3. RQ4 (Table 7 & Figure 9b) — Sensitivity Sweep $(k, \theta)$**
  - Lưới: $k \in \{1, 3, 5, 9\} \times \theta \in \{0.3, 0.5, 0.7\}$ (`temperature=0.3`)
  - Output: `results_paper_ec2/rq4_sweep_<agent>/rq4_sweep.json` & `tab_rq4_sweep.tex`

---

### Phase 6: Tổng hợp Bảng/Biểu đồ, Kiểm tra Provenance & Hoàn thiện Paper
- [ ] **6.1. Sinh toàn bộ bảng LaTeX và biểu đồ từ `trials.jsonl` thật**
  ```bash
  python ProvGuard/scripts/make_tables.py \
    --trials results_paper_ec2/table8_ui-tars/trials.jsonl \
    --out results_paper_ec2/tables \
    --sections-out sections/results

  python ProvGuard/scripts/make_figures.py \
    --trials results_paper_ec2/table8_ui-tars/trials.jsonl \
    --out figures/paper_results
  ```
- [ ] **6.2. Kiểm tra tính toàn vẹn kết quả (Result Integrity & Provenance)**
  ```bash
  python ProvGuard/scripts/check_runs.py --dir results_paper_ec2
  ```
  - Đảm bảo có đủ: `manifest.json` đã freeze, AOSP build fingerprint, `aosp_tcb=true`, raw transcripts, $k$ gate samples, binder logs.
- [ ] **6.3. Cập nhật `sections/experiments.tex` & compile lại `main.pdf`**
  - Thay số liệu thật vào `tab:res-asr`, `tab:res-utility`, `fig:conceptual` (bỏ `pgfplots_placeholder_results.tex` và xóa box `Status: The experiments in this section have not been run` ở dòng 9 `sections/experiments.tex`).
  - Biên dịch lại `main.tex` → `main.pdf`.
