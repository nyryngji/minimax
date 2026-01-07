import torch
import torch.nn as nn
import math

device = "cuda" if torch.cuda.is_available() else "cpu"
checkpoint = torch.load('D:\minimax\molecule_generation\\transformer_parameter\model_checkpoint_no_chemberta.pt', map_location=device, weights_only=False)

token2id = checkpoint['token2id']
id2token = checkpoint['id2token']

class PositionalEncoding(nn.Module): 
    def __init__(self, dim_model, dropout_p, max_len=512):
        super().__init__()
        self.dim_model = dim_model
        self.dropout = nn.Dropout(dropout_p)
        self.max_len = max_len
        self.register_buffer("pos_encoding", self._build_pos_encoding(max_len, dim_model))

    def _build_pos_encoding(self, max_len, dim_model):
        pos_encoding = torch.zeros(max_len, dim_model)
        positions_list = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        division_term = torch.exp(torch.arange(0, dim_model, 2).float() * (-math.log(10000.0) / dim_model))

        pos_encoding[:, 0::2] = torch.sin(positions_list * division_term)
        pos_encoding[:, 1::2] = torch.cos(positions_list * division_term)
        return pos_encoding.unsqueeze(0) 

    def forward(self, token_embedding: torch.Tensor) -> torch.Tensor:
        seq_len = token_embedding.size(1)
        if seq_len > self.pos_encoding.size(1):
            self.pos_encoding = self._build_pos_encoding(seq_len, self.dim_model).to(token_embedding.device)
        return self.dropout(token_embedding + self.pos_encoding[:, :seq_len, :])


class Transformer(nn.Module):
    def __init__(self, num_tokens, dim_model, num_heads,
                 num_encoder_layers, num_decoder_layers, dropout_p,
                 max_len=512):
        super().__init__()

        self.dim_model = dim_model
        self.positional_encoder = PositionalEncoding(
            dim_model=dim_model,
            dropout_p=dropout_p,
            max_len=max_len 
        )
        self.embedding = nn.Embedding(num_tokens, dim_model)

        self.transformer = nn.Transformer(
            d_model=dim_model,
            nhead=num_heads,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dropout=dropout_p,
        )
        self.out = nn.Linear(dim_model, num_tokens)

    def forward(self, src, tgt, tgt_mask=None, src_pad_mask=None, tgt_pad_mask=None):
        # Embedding + positional encoding
        src = self.embedding(src) * math.sqrt(self.dim_model)
        tgt = self.embedding(tgt) * math.sqrt(self.dim_model)
        src = self.positional_encoder(src)
        tgt = self.positional_encoder(tgt)

        src = src.permute(1, 0, 2)
        tgt = tgt.permute(1, 0, 2)

        # Transformer
        transformer_out = self.transformer(
            src, tgt,
            tgt_mask=tgt_mask,
            src_key_padding_mask=src_pad_mask,
            tgt_key_padding_mask=tgt_pad_mask
        )  # (seq, batch, dim)

        # (seq, batch, dim) → (batch, seq, vocab)
        out = self.out(transformer_out).permute(1, 0, 2)
        return out

    def get_tgt_mask(self, size) -> torch.Tensor:
        mask = torch.tril(torch.ones(size, size)).to(torch.bool)
        mask = mask.float()
        mask = mask.masked_fill(mask == 0, float('-inf'))
        mask = mask.masked_fill(mask == 1, float(0.0))
        return mask

    def create_pad_mask(self, matrix: torch.Tensor, pad_token: int) -> torch.Tensor:
        return (matrix == pad_token)

# 모델 예측 함수
def predict(
    model,
    input_sequence,
    max_length=66,
    SOS_token=token2id['[SOS]'],
    EOS_token=token2id['[EOS]'],
    PAD_token=token2id['[PAD]'],
    device=device
):
    model.eval()
    input_sequence = input_sequence.to(device)

    # batch size
    batch_size = input_sequence.size(0)

    # decoder input: [SOS]
    y_input = torch.full(
        (batch_size, 1),
        SOS_token,
        dtype=torch.long,
        device=device
    )

    finished = torch.zeros(batch_size, dtype=torch.bool, device=device)

    with torch.no_grad():
        for _ in range(max_length - 1):

            tgt_mask = model.get_tgt_mask(y_input.size(1)).to(device)
            src_pad_mask = model.create_pad_mask(input_sequence, PAD_token)
            tgt_pad_mask = model.create_pad_mask(y_input, PAD_token)

            pred = model(
                input_sequence,
                y_input,
                tgt_mask=tgt_mask,
                src_pad_mask=src_pad_mask,
                tgt_pad_mask=tgt_pad_mask
            )

            # greedy decoding (SMILES 안정성 최우선)
            logits = pred[:, -1, :]
            next_token = logits.argmax(dim=-1, keepdim=True)

            # EOS 이후는 PAD로 고정
            next_token[finished] = PAD_token
            finished |= (next_token.squeeze(1) == EOS_token)

            y_input = torch.cat([y_input, next_token], dim=1)

            if finished.all():
                break

    return y_input.squeeze(0).tolist()