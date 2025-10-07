import torch
import torch.nn as nn
import math

device = "cuda" if torch.cuda.is_available() else "cpu"
checkpoint = torch.load('D:\minimax원본\molecule_generation\\transformer_parameter\model_checkpoint.pt', map_location=device, weights_only=False)
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
def predict(model, input_sequence, max_length=66, 
            SOS_token=token2id['[SOS]'], 
            EOS_token=token2id['[EOS]'],
            temperature=1.0):  # temperature 추가
    model.eval()
    
    y_input = torch.tensor([[SOS_token]], dtype=torch.long, device=device)
    
    with torch.no_grad():
        for _ in range(max_length):
            tgt_mask = model.get_tgt_mask(y_input.size(1)).to(device)
            pred = model(input_sequence, y_input, tgt_mask)
            
            # Temperature scaling 적용
            logits = pred[0, -1, :] / temperature
            probs = torch.softmax(logits, dim=-1)
            
            # Top-k sampling (다양성 증가)
            top_k = 10
            top_probs, top_indices = torch.topk(probs, top_k)
            top_probs = top_probs / top_probs.sum()
            
            next_item = top_indices[torch.multinomial(top_probs, 1)].item()
            next_item = torch.tensor([[next_item]], device=device)
            
            y_input = torch.cat((y_input, next_item), dim=1)
            
            if next_item.view(-1).item() == EOS_token:
                break
    
    return y_input.view(-1).tolist()