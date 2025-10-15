import torch
import torch.nn as nn

class BAPULM(nn.Module):
    def __init__(self, input_dim=1792, hidden_dim=512):  # ← input_dim 추가
        super(BAPULM, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),  # 입력 차원
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)  # 출력은 1 (affinity score)
        )

    def forward(self, x):
        return self.fc(x)
