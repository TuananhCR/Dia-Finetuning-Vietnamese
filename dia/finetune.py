import argparse
import logging
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch
import torchaudio
import pandas as pd
from torch.utils.data import Dataset, DataLoader, random_split
from torch.cuda.amp import autocast
from torch.utils.tensorboard import SummaryWriter
from torch.nn.utils import clip_grad_norm_
from transformers import get_scheduler
import torch.nn.functional as F
import bitsandbytes as bnb
from tqdm import tqdm
from datasets import load_dataset, interleave_datasets, get_dataset_config_names, DatasetDict
from huggingface_hub import hf_hub_download
import math
import gc
from torch.cuda.amp import GradScaler

import dac
from .config import DiaConfig
from .layers import DiaModel
from .model import Dia
from .audio import build_delay_indices, apply_audio_delay
from .dataset import *
from .interleaved_datasets import load_cml_tts_streamed, load_common_voice17_streamed
from datasets import load_from_disk
from .dataset import HFDiaDataset
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.backends.cudnn.benchmark = True

#bytes for language tag replacement
LANG2BYTE = {
    "en": 3,
    "vi": 19,
}

CHANNELS = [
    "5phutcrypto",
    "anhbanthan",
    "anhthamtu",
    "animerewind.official",
    "bibitv8888",
    "btvgo",
    "baclieutv",
    "bachhoaxanhcom",
    "baodientuvov",
    "blvckvines",
    "boringppl",
    "bronub",
    "cdteam-why",
    "cobabinhduong",
    "cosmicwriter",
    "cuthongthai",
    "daiphatthanhtruyenhinhsonla",
    "day-be-thong-minh-tv",
    "danangtv",
    "daihanoi-htv",
    "daiptththainguyentntv",
    "dongmauviet",
    "dongthaptv",
    "fptbongdaofficial",
    "fonosvietnam",
    "hieurotrong5phut-ntkt",
    "htvtintuc",
    "happyhidari",
    "hoabinhtvgo",
    "hocenglishonline",
    "hocvienbovagau",
    "hungyentvvngo",
    "huynhduykhuongofficial",
    "huynhlapofficial",
    "jvevermind",
    "kenhvtc16",
    "kiengiangtv",
    "khanhvyofficial",
    "kienthucquansu",
    "lamdongtv1",
    "lamvlog",
    "longantv-la34",
    "mangovid",
    "mensbay",
    "meovatcuocsonglnv",
    "meuchannel",
    "ntnvlogsnguyenthanhnam",
    "ngamradio",
    "nhanhac555",
    "nhantaidaiviet",
    "ptth-trt",
    "ptvtruyenhinhphutho",
    "phantichgame",
    "phephim",
    "phimhottk-l",
    "riwaylegal",
    "ruangao",
    "suckhoetamsinh",
    "sachbiquyethanhcong",
    "soisangbrightsidevietnamese",
    "spiderum",
    "spiderumbooks",
    "sukieskitchen",
    "tin3phut",
    "tranthanhtown",
    "tulemientay",
    "tayninhtv",
    "thainhitv",
    "thanhpahm",
    "thegioilaptop",
    "thepresentwriter",
    "tiengiangtivi",
    "tieubaobaothom",
    "tintucbitcoin247",
    "truyenhinhbinhphuoc-bptv",
    "truyenhinhyenbaiytv",
    "truyenhinhcaobang",
    "truyenhinhdaklakdrt",
    "truyenhinhdaknong1",
    "truyenhinhdienbien23.9",
    "truyenhinhkhanhhoa",
    "truyenhinhkontumkrt",
    "truyenhinhnaminhntv",
    "truyenhinhninhthuan",
    "truyenhinhquangngai",
    "tuantienti2911",
    "tuyenquangttv",
    "vovlivedoctruyen",
    "vietcetera",
    "vinhlongtv",
    "voizfm",
    "vutrunguyenthuy",
    "vuive",
    "w2wanime",
    "w2wcartoon",
    "w2whorror",
    "w2wmovie",
    "web5ngay",
    "xanh24h",
    "aiphatthanhtruyenhinhquangtri",
    "aiphatthanhvatruyenhinhhai1908",
    "altonghop",
    "antvtruyenhinhcongannhandan",
    "baihoc10phut",
    "battlecry.khampha",
    "betterversionvn",
    "blogkhoinghiep",
    "bumcn",
    "caikinhdi_vn",
    "canthitg",
    "chanthienmybachnien",
    "chauanhchao",
    "cosu",
    "cungmaivaobep-monan-amthuc",
    "daiptthphuyen",
    "daiptthtv",
    "daitruyenhinhangiang",
    "daitruyenhinhbacgiang",
    "dannytran2375",
    "daybehoc5489",
    "daylaphegame",
    "dienmay",
    "ducisreal",
    "duongfg",
    "duyluandethuong",
    "duythanhish",
    "elroydevops",
    "gc.gamelab",
    "hacthaybachthay",
    "hagiangtv475",
    "haiduongtv247",
    "hanamtv8831",
    "hangphimtailieudienanhnd",
    "haugiangtv",
    "haunauday",
    "hieu-tv",
    "hoshiphan",
    "jakinatsumi2915",
    "kechuyentieuhoc1719",
    "kenhcovan",
    "khalid_dinh",
    "kiaralah",
    "laichautv",
    "langsontvtube",
    "megame_official",
    "minvestvn",
    "nguoithanhcong1991",
    "nhatkycuocsong.",
    "ntcanima",
    "ptthbentre",
    "ptthquangbinh",
    "qrt",
    "quangninhtv",
    "snewsvn",
    "soctrangtv",
    "sunhuynpodcast",
    "tamhonanuong",
    "tgddreview",
    "thaibinhtv",
    "thanhnamedu",
    "thanhnientvnews",
    "thbrt",
    "thieunhitv3630",
    "thtpct",
    "tinnhanh3phut868",
    "toansam",
    "toidicodedaoblog",
    "tranquochuywecommit",
    "tranvyvy",
    "truyenhinh4k",
    "truyenhinhbinhthuan",
    "truyenhinhcamau69",
    "truyenhinhdongnai_dnrtv",
    "truyenhinhgialai",
    "truyenhinhlaocai",
    "truyenhinhnghean",
    "truyenhinhvinhphuc",
    "txtofficial8798",
    "vanhkhuyenle",
    "vietnh1009",
    "visaothenhipodcast",
    "vtc14",
    "vtcnow",
    "vtv24",
    "vuive123",
    "zombiev4",
]

# Tự động ánh xạ channel → token (bắt đầu từ 30)
for i, ch in enumerate(CHANNELS):
    LANG2BYTE[ch] = 30 + i

test_sentences = {
    "en": "In order to fully assess performance and the accuracy of language tags, this test sentence contains multiple subordinate clauses, varied punctuation, and a sufficient word count.",
    "vi": "Để đánh giá toàn diện hiệu suất và độ chính xác của các thẻ ngôn ngữ, câu kiểm tra này chứa nhiều mệnh đề phụ, dấu câu đa dạng và số lượng từ đầy đủ."
}

@dataclass
class TrainConfig:
    epochs: int = 1
    batch_size: int = 2
    grad_accum_steps: int = 2
    learning_rate: float = 1e-5
    warmup_steps: int = 500
    unconditional_frac: float = 0.15
    eval_step: int = 200
    save_step: int = 2000
    split_ratio: float = 0.997
    shuffle_buffer_size: int = None  # for streaming shuffle
    seed: int = 42                # seed for reproducibility
    runs_dir: Path = Path("runs")
    run_name: str = "dia_finetune_cv"
    output_dir: Path = Path(".cpkts/dia_finetune_cv ")
    resume_from: Path = None  
    total_steps: int = 290007



def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Dia audio model")
    parser.add_argument("--config",    type=Path, default=Path("dia/config.json"))
    parser.add_argument("--dataset",   type=str,  default="Paradoxia/opendata-iisys-hui",
                        help="HuggingFace dataset name (if not using --csv_path).")
    parser.add_argument("--dataset2",  type=str,  default=None,
                        help="(Optional) second HF dataset to interleave (streaming)")
    parser.add_argument("--streaming",action="store_true",
                        help="Enable HuggingFace dataset streaming")
    parser.add_argument("--hub_model", type=str,  default="nari-labs/Dia-1.6B")
    parser.add_argument("--local_ckpt", type=str,  default=None)
    parser.add_argument("--csv_path",  type=Path, default=None,
                        help="Path to local CSV/TSV file with `audio|text` (if you want to train locally).")
    parser.add_argument("--audio_root",type=Path, default=None,
                        help="Root directory for local audio files (required if --csv_path is set).")
    parser.add_argument("--run_name",  type=str,  default=None)
    parser.add_argument("--output_dir",type=Path, default=None)
    parser.add_argument("--shuffle_buffer_size", type=int, default=None,
                        help="Buffer size for streaming dataset shuffle.")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility.")
    parser.add_argument("--half", action="store_true", help="load model in fp16")
    parser.add_argument("--compile", action="store_true", help="torch compile model")
    parser.add_argument('--use_amp', action='store_true', help='Enable mixed precision')
    parser.add_argument("--resume_from", type=str, default=None)
    return parser.parse_args()



def collate_fn(batch, config: DiaConfig, device: torch.device):
    from torch.nn.functional import pad

    texts, encodings, waveforms = zip(*batch)

    # -- Text inputs ---------------------------------------------------------

    max_text = config.data.text_length
    pad_tok = config.data.text_pad_value
    text_ids = []
    for txt in texts:
        b_full = txt.encode('utf-8')
        # replace leading "[lang]" prefix
        for code, val in LANG2BYTE.items():
            prefix = f"[{code}]".encode('utf-8')
            if b_full.startswith(prefix):
                b_full = bytes([val]) + b_full[len(prefix):]
                break
        bts = b_full[:max_text]
        arr = list(bts) + [pad_tok] * (max_text - len(bts))
        text_ids.append(torch.tensor(arr, dtype=torch.long))
    src = torch.stack(text_ids).to(device)
    src_pos = torch.arange(max_text, device=device).unsqueeze(0).expand(src.size(0), -1)
    src_pad = src.ne(pad_tok)
    enc_self_attn_mask = (src_pad.unsqueeze(2) & src_pad.unsqueeze(1)).unsqueeze(1)

    # -- Audio codes --------------------------------------------------------

    max_audio = config.data.audio_length
    # per-sample lengths (clipped to max_audio)
    seq_lens = [min(e.size(0), max_audio) for e in encodings]
    batch_max = max(seq_lens)

    # pad or trim each encoding to the batch max length
    padded = [pad(e, (0, 0, 0, batch_max - e.size(0))) if e.size(0) < batch_max else e[:batch_max]
              for e in encodings]
    codes = torch.stack(padded).to(device)  # (B, T=batch_max, C)

    B, T, C = codes.shape
    t_idx, idxs = build_delay_indices(B, T, C, config.data.delay_pattern)
    delayed = apply_audio_delay(
        codes,
        config.data.audio_pad_value,
        config.data.audio_bos_value,
        (t_idx, idxs)
    )
    # ensure no longer than max_audio
    delayed = delayed[:, :max_audio, :]

    # -- Targets with per-sample EOS ----------------------------------------

    max_tgt_len = max_audio + 2
    pad_val = config.data.audio_pad_value
    bos_val = config.data.audio_bos_value
    eos_val = config.data.audio_eos_value

    tgt = torch.full((B, max_tgt_len, C), pad_val, dtype=torch.long, device=device)
    tgt[:, 0, :] = bos_val
    tgt_lens = []
    for i, L in enumerate(seq_lens):
        tgt[i, 1:1 + L, :] = delayed[i, :L, :]
        tgt[i, 1 + L, :] = eos_val
        tgt_lens.append(1 + L + 1)

    tgt_pos = torch.arange(max_tgt_len, device=device).unsqueeze(0).expand(B, -1)
    tgt_pad = tgt.ne(pad_val).any(-1)

    causal = torch.tril(torch.ones((max_tgt_len, max_tgt_len),
                                    dtype=torch.bool,
                                    device=device))
    dec_self_attn_mask = (tgt_pad.unsqueeze(2) & tgt_pad.unsqueeze(1) & causal).unsqueeze(1)
    dec_cross_attn_mask = (tgt_pad.unsqueeze(2) & src_pad.unsqueeze(1)).unsqueeze(1)

    return {
        'src_tokens': src,
        'src_positions': src_pos,
        'enc_self_attn_mask': enc_self_attn_mask,
        'tgt_tokens': tgt,
        'tgt_positions': tgt_pos,
        'dec_self_attn_mask': dec_self_attn_mask,
        'dec_cross_attn_mask': dec_cross_attn_mask,
        'waveforms': waveforms,
        'raw_text': texts[0],
        'tgt_lens': torch.tensor(tgt_lens, dtype=torch.long, device=device),
    }

def setup_loaders(dataset, dia_cfg: DiaConfig, train_cfg: TrainConfig, device):
    collate = lambda b: collate_fn(b, dia_cfg, device)
    if isinstance(dataset, HFDiaIterDataset):
        total = getattr(dataset, "total_examples", None)
        if total is None:
            total = dataset.dataset.info.splits["train"].num_examples
        n_train = int(train_cfg.split_ratio * total)
        n_val = total - n_train
        if n_val <= 0:
            raise RuntimeError(f"No validation samples: total={total}, split_ratio={train_cfg.split_ratio}")
        base = dataset.dataset.shuffle(buffer_size=train_cfg.shuffle_buffer_size, seed=train_cfg.seed) if train_cfg.shuffle_buffer_size else dataset.dataset
        val_stream = base.take(n_val)
        train_stream = base.skip(n_val)
        train_ds = HFDiaIterDataset(train_stream, dia_cfg, dataset.dac_model)
        val_ds = HFDiaIterDataset(val_stream, dia_cfg, dataset.dac_model)
        train_loader = DataLoader(train_ds, batch_size=train_cfg.batch_size, shuffle=False, collate_fn=collate)
        train_loader.steps_per_epoch = math.ceil(n_train / train_cfg.batch_size)
        val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, collate_fn=collate)
        return train_loader, val_loader
    ds_len = len(dataset)
    n_train = int(train_cfg.split_ratio * ds_len)
    train_ds, val_ds = random_split(dataset, [n_train, ds_len - n_train])
    train_loader = DataLoader(train_ds, batch_size=train_cfg.batch_size, shuffle=True, collate_fn=collate)
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, collate_fn=collate)
    return train_loader, val_loader



def setup_optimizer_and_scheduler(model, train_loader, train_cfg):
    opt = bnb.optim.AdamW8bit(model.parameters(), lr=train_cfg.learning_rate)
    # Determine steps per epoch: prefer len(), else use attached attribute
    try:
        steps_per_epoch = len(train_loader)
    except TypeError:
        if hasattr(train_loader, 'steps_per_epoch'):
            steps_per_epoch = train_loader.steps_per_epoch
        else:
            raise RuntimeError("Cannot determine steps_per_epoch for streaming loader")
    total_training_steps = steps_per_epoch * train_cfg.epochs
    sched = get_scheduler(
        'cosine', opt,
        num_warmup_steps=train_cfg.warmup_steps / train_cfg.grad_accum_steps,
        num_training_steps=total_training_steps / train_cfg.grad_accum_steps
    )
    return opt, sched



def train_step(model, batch, dia_cfg, train_cfg, opt, sched, writer, step_in_epoch, global_step,scaler):
    """
    Perform a single training step: forward, loss, backward, update, log.
    Now uses per‑sample tgt_lens to mask out padding after each EOS,
    and applies 4× loss weight on the first channel.
    """
    # (optional) unconditional conditioning
    if random.random() < train_cfg.unconditional_frac:
        pad_tok = dia_cfg.data.text_pad_value
        batch['src_tokens'] = torch.zeros_like(batch['src_tokens'])
        batch['enc_self_attn_mask'] = torch.zeros_like(batch['enc_self_attn_mask'])
        batch['dec_cross_attn_mask'] = torch.zeros_like(batch['dec_cross_attn_mask'])

    with autocast(dtype=torch.float16):
        # forward pass
        logits = model(
            src_BxS=batch['src_tokens'],
            tgt_BxTxC=batch['tgt_tokens'],
            src_positions=batch['src_positions'],
            tgt_positions=batch['tgt_positions'],
            enc_self_attn_mask=batch['enc_self_attn_mask'],
            dec_self_attn_mask=batch['dec_self_attn_mask'],
            dec_cross_attn_mask=batch['dec_cross_attn_mask'],
            enable_dropout=True,
        )
        # fetch per-sample target‑lengths (including BOS+frames+EOS)
        lens = batch['tgt_lens']                   # shape: (B,)
        max_L = int(lens.max().item())             # maximum over batch

        # keep only up through the last possible EOS slot
        # logits: (B, T, C, V) -> (B, max_L-1, C, V)
        logits = logits[:, : max_L - 1]

        # targets: shift off the BOS so 0..<max_L-1> align with logits
        # target: (B, T, C) -> (B, max_L-1, C)
        target = batch['tgt_tokens'][:, 1:max_L, :]

        B, Tm1, C = target.shape
        pad_val = dia_cfg.data.audio_pad_value

        # build a mask [B x (max_L-1)] that is True for t < (lens[i]-1)
        time_idx = torch.arange(Tm1, device=lens.device).unsqueeze(0)  # (1, Tm1)
        valid_time = time_idx < (lens.unsqueeze(1) - 1)                # (B, Tm1)
        mask = valid_time.unsqueeze(-1).expand(-1, -1, C)             # (B, Tm1, C)

        # apply 4× weight on first channel, 1× on others
        channel_weights = [4.0] + [1.0] * (C - 1)
        loss_c = 0.0
        _, _, _, V = logits.size()

        for c, w in enumerate(channel_weights):
            # flatten this channel
            lc = logits[:, :, c, :].reshape(-1, V)   # (B*Tm1, V)
            tc = target[:, :, c].reshape(-1)         # (B*Tm1,)
            mc = mask[:, :, c].reshape(-1)           # (B*Tm1,)

            # mask out padding and compute cross-entropy
            lc_valid = lc[mc]
            tc_valid = tc[mc]
            loss_c += w * F.cross_entropy(
                lc_valid, tc_valid,
                ignore_index=pad_val
            )

        # normalize by sum of weights
        loss = loss_c / sum(channel_weights)

    # scale + backward
    loss = loss / train_cfg.grad_accum_steps
    scaler.scale(loss).backward()


    # step & log

    if (step_in_epoch + 1) % train_cfg.grad_accum_steps == 0:
        # Unscale before clipping
        scaler.unscale_(opt)
        grad_norm = clip_grad_norm_(model.parameters(), max_norm=1e9)
    
        scaler.step(opt)
        scaler.update()
        opt.zero_grad()
        sched.step()
    
        true_loss = loss.item() * train_cfg.grad_accum_steps
        current_lr = sched.get_last_lr()[0]
    
        writer.add_scalar('GradNorm/global', grad_norm, global_step)
        writer.add_scalar('LR', current_lr, global_step)
        writer.add_scalar('Loss/train', true_loss, global_step)
    
        return true_loss
    else:
        return loss.item() * train_cfg.grad_accum_steps




def eval_step(model, val_loader, dia_cfg, dac_model, writer, global_step):
    """
    Run evaluation: compute average loss on validation set and log audio samples.
    """
    import gc
    eval_losses = []
    last_batch = None
    with torch.inference_mode():
        for eb in tqdm(val_loader, desc="eval"):
            last_batch = eb

            with autocast(dtype=torch.float16):
                logits16 = model(
                    src_BxS=eb['src_tokens'],
                    tgt_BxTxC=eb['tgt_tokens'],
                    src_positions=eb['src_positions'],
                    tgt_positions=eb['tgt_positions'],
                    enc_self_attn_mask=eb['enc_self_attn_mask'],
                    dec_self_attn_mask=eb['dec_self_attn_mask'],
                    dec_cross_attn_mask=eb['dec_cross_attn_mask'],
                    enable_dropout=False,
                )[:, :-1]

            logits = logits16.float()
            target = eb['tgt_tokens'][:, 1:]
            B_e, T_e, C_e = target.shape
            V_e = logits.size(-1)

            loss_e = 0.0
            weights_e = [4.0] + [1.0] * (C_e - 1)
            for c, w in enumerate(weights_e):
                lc = logits[:, :, c, :].reshape(-1, V_e)
                tc = target[:, :, c].reshape(-1)
                loss_e += w * F.cross_entropy(
                    lc, tc, ignore_index=dia_cfg.data.audio_pad_value
                )
            loss_e = loss_e / sum(weights_e)

            eval_losses.append(loss_e)

    avg_eval_loss = sum(eval_losses) / len(eval_losses)
    writer.add_scalar('Loss/eval', avg_eval_loss.item(), global_step)

    # --- Inference test sentence ---
    try:
        orig_dtype = next(model.parameters()).dtype
        model = model.float()
        dia_gen = Dia(dia_cfg, device)
        dia_gen.model, dia_gen.dac_model = model, dac_model

        # ✅ Test câu hội thoại đa giọng
        test_dialogue = "[vtv24] Em vừa đi học về, anh ạ. [duongfg] Ừ, em ăn cơm chưa? [vtv24] Em ăn rồi!"
        
        if len(test_dialogue) > 10:
            try:
                audio = dia_gen.generate(text=test_dialogue)
                writer.add_audio("Eval/test_dialogue", audio, global_step, 44100)
            except Exception:
                logger.exception("Eval error during test_dialogue")
            finally:
                if 'audio' in locals():
                    del audio 


    except Exception:
        logger.exception("Eval error")

    finally:
        if 'audio' in locals():
            del audio
        gc.collect()
        torch.cuda.empty_cache()
        if orig_dtype == torch.float16:
            model = model.half()

def train(model, dia_cfg: DiaConfig, dac_model: dac.DAC, dataset, train_cfg: TrainConfig):
    """
    Run the full training loop over epochs.
    """
    # prepare directories
    train_cfg.output_dir.mkdir(parents=True, exist_ok=True)
    (train_cfg.runs_dir / train_cfg.run_name).mkdir(parents=True, exist_ok=True)
    model = model.to(device)

    train_loader, val_loader = setup_loaders(dataset, dia_cfg, train_cfg, device)
    opt, sched = setup_optimizer_and_scheduler(model, train_loader, train_cfg)

    writer = SummaryWriter(train_cfg.runs_dir / train_cfg.run_name)
    model.train()
    scaler = GradScaler()
    start_epoch = 0
    global_step = 0
    resume_ckpt = getattr(train_cfg, "resume_from", None)
    if resume_ckpt and resume_ckpt.exists():
        logger.info(f"Resuming from checkpoint: {resume_ckpt}")
        checkpoint = torch.load(resume_ckpt, map_location=device)
        model.load_state_dict(checkpoint["model"])
        opt.load_state_dict(checkpoint["optimizer"])
        sched.load_state_dict(checkpoint["scheduler"])
        scaler.load_state_dict(checkpoint["scaler"])
        start_epoch = checkpoint.get("epoch", 0)
        global_step = checkpoint.get("global_step", 0)


    steps_per_epoch = getattr(train_loader, 'steps_per_epoch', None)
    if steps_per_epoch is None:
        try:
            steps_per_epoch = len(train_loader)
        except Exception:
            steps_per_epoch = None

    for epoch in range(start_epoch, train_cfg.epochs):
        # iterate with progress bar, using total if known
        loader_iter = tqdm(
            train_loader,
            desc=f"E{epoch+1}",
            total=steps_per_epoch
        )
        pbar = tqdm(loader_iter, total=train_cfg.total_steps, initial=global_step, desc=f"E{epoch}")
        for step_in_epoch, batch in enumerate(pbar):
            global_step += 1
            # training step
            loss = train_step(model, batch, dia_cfg, train_cfg, opt, sched, writer, step_in_epoch, global_step, scaler)

            cur_alloc = torch.cuda.memory_allocated()   # bytes currently allocated by tensors
            peak_alloc = torch.cuda.max_memory_allocated()  # bytes peak during program
            # optionally convert to GB
            cur_gb  = cur_alloc  / 1024**3
            peak_gb = peak_alloc / 1024**3

            # update the tqdm postfix
            loader_iter.set_postfix({
                'loss': f"{loss:.4f}",
                'VRAM (GB)': f"{cur_gb:.2f}/{peak_gb:.2f}"
            })

            # remember to zero the peak if you want rolling peaks per step
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()

            
            # evaluation
            if step_in_epoch % train_cfg.eval_step == 0:
                model.eval()
                with torch.no_grad():
                    eval_step(model, val_loader, dia_cfg, dac_model, writer, global_step)
                model.train()
                scaler = GradScaler()

            # checkpoint
            if step_in_epoch and step_in_epoch % train_cfg.save_step == 0:
                ckpt = train_cfg.output_dir / f"ckpt_step{global_step}.pth"
                torch.save({
                    "model": model.state_dict(),
                    "optimizer": opt.state_dict(),
                    "scheduler": sched.state_dict(),
                    "scaler": scaler.state_dict(),
                    "epoch": epoch,
                    "global_step": global_step
                }, ckpt)
                logger.info(f"Saved checkpoint: {ckpt}")

        # end of epoch checkpoint
        ckpt_e = train_cfg.output_dir / f"ckpt_epoch{epoch+1}.pth"
        torch.save({
            "model": model.state_dict(),
            "optimizer": opt.state_dict(),
            "scheduler": sched.state_dict(),
            "scaler": scaler.state_dict(),
            "epoch": epoch + 1,
            "global_step": global_step
        }, ckpt_e)
        logger.info(f"Saved end-of-epoch checkpoint: {ckpt_e}")

from datasets import disable_caching

def main():
    args = get_args()
    import os
    os.environ["HF_DATASETS_CACHE"] = "/tmp/force_streaming"  # ép cache mới  
    disable_caching()
  # tắt toàn bộ cache local HuggingFace
    import json
    with open(args.config, "r", encoding="utf-8") as f:
        config_dict = json.load(f)

    dia_cfg = DiaConfig(**config_dict)
    dac_model = dac.DAC.load(dac.utils.download()).to(device)
    dataset = None

    if not dataset:
        if args.csv_path:
            if not args.audio_root:
                raise ValueError("`--audio_root` must be set when using `--csv_path`")
            dataset = LocalDiaDataset(args.csv_path, args.audio_root, dia_cfg, dac_model)
        else:
            # ✅ Check nếu dataset là đường dẫn local
            if Path(args.dataset).exists():
                print(f"Loading dataset from local path: {args.dataset}")
                ds1 = load_from_disk(args.dataset)
                if isinstance(ds1, DatasetDict):
                    ds1 = ds1["train"]
                dataset = HFDiaDataset(ds1, dia_cfg, dac_model)
            else:
                print(f"Loading HuggingFace dataset: {args.dataset} (streaming)")
                ds1 = load_dataset(args.dataset, split="train", streaming=True)
    
                if args.dataset2:
                    ds2 = load_dataset(args.dataset2, split="train", streaming=True)
                    hf_ds = interleave_datasets([ds1, ds2])
                    dataset = HFDiaIterDataset(hf_ds, dia_cfg, dac_model)
                else:
                    hf_ds = ds1
                    dataset = HFDiaIterDataset(hf_ds, dia_cfg, dac_model)

    

    train_cfg = TrainConfig(
        run_name   = args.run_name   or TrainConfig.run_name,
        output_dir = args.output_dir or TrainConfig.output_dir,
        shuffle_buffer_size = args.shuffle_buffer_size,
        seed = args.seed,
    )
    if args.resume_from:
        train_cfg.resume_from = Path(args.resume_from)
    # load model checkpoint
    if args.local_ckpt:
        ckpt_file = args.local_ckpt
    else:
        ckpt_file = hf_hub_download(args.hub_model, filename="dia-v0_1.pth")
    model = DiaModel(dia_cfg)
    if args.half:
        model=model.half()
    if args.compile:
        model = torch.compile(model, backend="inductor")
    ckpt = torch.load(ckpt_file, map_location="cpu")
    state_dict = ckpt["model"] if "model" in ckpt else ckpt
    new_state_dict = {}
    
    for k, v in state_dict.items():
        if "encoder.embedding.weight" in k:
            if v.shape != model.state_dict()[k].shape:
                print(f"⚠️ Bỏ qua {k} do shape không khớp: {v.shape} vs {model.state_dict()[k].shape}")
                continue
        new_state_dict[k] = v
    
    model.load_state_dict(new_state_dict, strict=False)
    

    # start training
    train(model, dia_cfg, dac_model, dataset, train_cfg)


if __name__ == "__main__":
    main()
