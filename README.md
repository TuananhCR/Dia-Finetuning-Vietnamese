# 🇻🇳 Dia TTS – Fine-Tuning Vietnamese

High‑quality Vietnamese speech generation 44.1 kHz on top of Nari Labs’ DIA 1.6B. This repo provides an unofficial fine‑tune enabling natural Vietnamese with controllable style, multi‑speaker accents, and a friendly Gradio demo.

---

⚠️ Status: Community release. Upstream DIA currently ships English generation; this project adds Vietnamese via fine‑tuning. Follow ethical use guidelines below.
- Maintainer: Tuan Anh — AI/ML Researcher @ Appota SRD (R&D Department)
- Compute: Trained and developed on Appota’s server infrastructure



https://github.com/user-attachments/assets/8e5604eb-e3b7-4cee-99e6-f18dfd546788



## Features

- ✅ Fine-tune model Dia 1.6B with Vietnamese Dataset
- ✅ Support single speaker and multispeaker with various Vietnamese accent ( Nort-male, South-male, North-female and South-female)
- ✅ Adjusting voice generate by `temperature`, `top_p`, `cfg_scale`, etc.
- ✅ Friendly Gradio Inference
- ✅ Speed up by `torch.compile`, `bfloat16`, 8-bit optimizer
---
- You can try demo at : https://huggingface.co/spaces/cosrigel/Dia-Vietnamese
- You can use our finetune model at : https://huggingface.co/cosrigel/dia-finetuning-vnese
---

## Data Preparation for Finetuning model
- Audio: mono 44.1 kHz WAV/FLAC; per‑utterance 3–20 s; peak‑normalized.
- Dataset finetuned : cosrigel/vn_tts_medium_clean

### Training Configuration:
- Base model : nari-labs/Dia-1.6B
- GPU : NVIDIA RTX A6000
- You can use our checkpoint to use the inference at : https://huggingface.co/cosrigel/dia-finetuning-vnese

## Inference Tips (Vietnamese)
- Transcripts: begin with [01] or [KienThucQuanSu] then text
- For example: [KienThucQuanSu] Thủ tướng cũng yêu cầu các Bộ, cơ quan trung ương, địa phương tăng cường công tác thanh tra, kiểm tra việc sắp xếp, xử lý tài sản trước, trong và sau khi sắp xếp tổ chức bộ máy, sắp xếp đơn vị hành chính.
- Multispeaker: [KienThucQuanSu] Thủ tướng cũng yêu cầu các Bộ, cơ quan trung ương, địa phương tăng cường công tác thanh tra.[CoBaBinhDuong] Kiểm tra việc sắp xếp, xử lý tài sản trước, trong và sau khi sắp xếp tổ chức bộ máy, sắp xếp đơn vị hành chính.
- You can lookup the speaker ID in speaker table ID which is already existed in Gradio Inference
- With Multispeaker , you can change the speaker with speaker's tag. Make sure it after the dot. 
<img width="1545" height="903" alt="Screenshot 2025-08-16 at 09 53 21" src="https://github.com/user-attachments/assets/42a24781-0aaf-402d-aa37-901f0046c9cc" />

## Future Feature Improve
- ☐ Increase the quality of voice-cloning
- ☐ Add emotion to dataset and model so you can you emotion's tag like : [cười], [khóc], [ho],...
- ☐ Adjust the voice of multispeaker so they can sound like they're all in one room speaking to each other.

## Ethics & Responsible Use
- Obtain consent for any real person’s voice.
- Disclose synthetic audio in production settings.
- No impersonation, harassment, or deceptive content.

## 🛠️ Guide for Installation ( Hướng dẫn cho người mới sử dụng cài đặt model chạy inference ) 

### Requirements
- Free up 150GB storage
- 16GB RAM
- GPU or MPS required ( CPU is very slow and we don't recommend )

### Bước 1: Nhập bash vào terminal để cài đặt Git Repo

```bash
git clone https://github.com/TuananhCR/Dia-Finetuning-Vietnamese
python -m venv .venv
source .venv/bin/activate
pip install -e .
```
### Bước 2: Login hugging face và tạo access token
- Các bác mới sử dụng hugging face cần tạo tài khoản và login vào , sau đó vào link https://huggingface.co/cosrigel/dia-finetuning-vnese
- Đồng ý Agree to share your contact information to access to this model.
- Sau đó vào góc trên bên phải có hình cá nhân mình, nhấn vào phía dưới có Access Token, tạo riêng bản thân một token và NHỚ SAO CHÉP LẠI (KHÔNG PUBLIC) nó sẽ là dạng :  hf_XXXXXXXXXcKXXXXXXXXX

<img width="1275" height="734" alt="Screenshot 2025-08-18 at 12 02 35" src="https://github.com/user-attachments/assets/09b8d1d9-5c68-43ac-a258-ca691ebad02e" />


### Bước 3: Tải và cài đặt safetensors
```bash
python -m pip install -U "huggingface_hub[cli]"
huggingface-cli login --token <Thay bằng hf__ của các bạn vừa sao chép> --add-to-git-credential
python -c 'from huggingface_hub import snapshot_download; snapshot_download("cosrigel/dia-finetuning-vnese", local_dir="dia", repo_type="model")'
```
### Bước 4: chạy inference chờ model load và thưởng thức.
```bash
python app_local.py
```
### NOTE: 
- Khuyến khích sử dụng **CUDA** để chạy hoặc nếu sử dụng ( MPS hoặc CPU ) thời gian generate sẽ khá lâu. 
- Thời gian load đã đo được:
+ 1000 từ sử dụng cuda, GPU RTX A6000 sẽ mất 79 giây

```bash
python app_local.py --device cpu
```

## Usage Example Training
```bash
python finetune.py \
  --config configs/config.json \
  --dataset  \
  --hub_model nari-labs/Dia-1.6B \
  --run_name dia_vietnamese_experiment \
  --output_dir ./checkpoints
```

## Acknowledgements
- Appota SRD (R&D Department) — compute & infrastructure support for training and development
- Nari Labs – DIA (architecture & checkpoints)
- Descript Audio Codec (DAC) for discrete audio tokens
- Hugging Face Transformers/PEFT/Accelerate

## Citation
```
If you use this work, please cite the upstream DIA model and this repository.
@misc{Dia-Finetuning-Vietnamese,
  title        = {DIA Vietnamese Fine-Tuning} ,
  author       = {Cos Rigel},
  year         = {2025},
  howpublished = {GitHub repository},{Huggingface repository}
  url          = {https://github.com/TuananhCR/Dia-Finetuning-Vietnamese}
}
```
