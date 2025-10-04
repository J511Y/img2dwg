"""CAD JSON 특화 토크나이저."""

from typing import List, Optional
from transformers import AutoTokenizer, PreTrainedTokenizer


class CADTokenizer:
    """
    CAD JSON 생성을 위한 특화 토크나이저.
    
    GPT2 토크나이저를 확장하여 CAD 관련 특수 토큰을 추가한다.
    """
    
    # CAD 특화 토큰
    CAD_TOKENS = [
        # JSON 구조 토큰
        "{", "}", "[", "]", ":", ",",
        
        # 엔티티 타입
        "LINE", "POLYLINE", "LWPOLYLINE", "ARC", "CIRCLE",
        "TEXT", "MTEXT", "INSERT", "DIMENSION",
        
        # 속성 키
        "type", "start", "end", "points", "center", "radius",
        "position", "content", "height", "layer", "color",
        
        # 레이어명 (자주 사용되는 것들)
        "Wall", "Door", "Window", "Dimension", "Text",
        "0",  # 기본 레이어
        
        # 좌표 관련
        "x", "y", "z",
        
        # 메타데이터
        "metadata", "filename", "entities",
    ]
    
    def __init__(
        self,
        base_model: str = "gpt2",
        add_special_tokens: bool = True,
    ):
        """
        CADTokenizer를 초기화한다.
        
        Args:
            base_model: 기본 토크나이저 모델명
            add_special_tokens: CAD 특수 토큰 추가 여부
        """
        self.tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(base_model)
        
        # Padding 토큰 설정 (GPT2는 기본적으로 없음)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        # CAD 특수 토큰 추가
        if add_special_tokens:
            num_added = self.tokenizer.add_tokens(self.CAD_TOKENS)
            print(f"Added {num_added} CAD-specific tokens to tokenizer")
    
    def __call__(self, *args, **kwargs):
        """토크나이저 호출을 래핑한다."""
        return self.tokenizer(*args, **kwargs)
    
    def encode(self, text: str, **kwargs) -> List[int]:
        """텍스트를 토큰 ID로 인코딩한다."""
        return self.tokenizer.encode(text, **kwargs)
    
    def decode(self, token_ids: List[int], **kwargs) -> str:
        """토큰 ID를 텍스트로 디코딩한다."""
        return self.tokenizer.decode(token_ids, **kwargs)
    
    def batch_encode(self, texts: List[str], **kwargs):
        """배치 인코딩."""
        return self.tokenizer(texts, **kwargs)
    
    def batch_decode(self, token_ids_list: List[List[int]], **kwargs) -> List[str]:
        """배치 디코딩."""
        return self.tokenizer.batch_decode(token_ids_list, **kwargs)
    
    @property
    def vocab_size(self) -> int:
        """어휘 크기를 반환한다."""
        return len(self.tokenizer)
    
    @property
    def pad_token_id(self) -> int:
        """Padding 토큰 ID를 반환한다."""
        return self.tokenizer.pad_token_id
    
    @property
    def eos_token_id(self) -> int:
        """EOS 토큰 ID를 반환한다."""
        return self.tokenizer.eos_token_id
    
    @property
    def bos_token_id(self) -> int:
        """BOS 토큰 ID를 반환한다."""
        return self.tokenizer.bos_token_id
    
    def save_pretrained(self, save_directory: str):
        """토크나이저를 저장한다."""
        self.tokenizer.save_pretrained(save_directory)
    
    @classmethod
    def from_pretrained(cls, model_path: str) -> "CADTokenizer":
        """저장된 토크나이저를 로드한다."""
        instance = cls.__new__(cls)
        instance.tokenizer = AutoTokenizer.from_pretrained(model_path)
        return instance
