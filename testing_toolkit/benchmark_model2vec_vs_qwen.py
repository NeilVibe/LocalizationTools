#!/usr/bin/env python3
"""
Model2Vec vs Qwen Benchmark
============================

Compares semantic search quality and performance:
- Model2Vec (potion-multilingual-128M) - lightweight ~128MB
- Qwen (Qwen3-Embedding-0.6B) - heavy ~2.3GB

Test: 500 queries against 5000 TM entries (Korean source)

Run: python3 testing_toolkit/benchmark_model2vec_vs_qwen.py
"""

import sys
import time
import gc
import psutil
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test data - Korean source with semantic variations
SEMANTIC_TEST_PAIRS = [
    # (query, should_match, description)
    ("저장", "저장하기", "Save variations"),
    ("저장하기", "저장하시겠습니까?", "Save dialog"),
    ("세이브", "저장", "Save synonym (Korean loanword vs native)"),
    ("취소", "취소하기", "Cancel variations"),
    ("삭제", "지우기", "Delete synonyms"),
    ("확인", "확인하시겠습니까?", "Confirm dialog"),
    ("로그인", "로그인하기", "Login variations"),
    ("비밀번호", "패스워드", "Password synonyms"),
    ("시작", "시작하기", "Start variations"),
    ("종료", "끝내기", "End synonyms"),
    ("설정", "환경설정", "Settings variations"),
    ("파일", "파일을 선택해 주세요", "File context"),
    ("오류", "에러가 발생했습니다", "Error message"),
    ("성공", "작업이 완료되었습니다", "Success message"),
    ("네트워크", "인터넷 연결을 확인해 주세요", "Network context"),
]

# Extended Korean TM-like phrases for corpus
KOREAN_TM_CORPUS = [
    "저장하기", "저장하시겠습니까?", "변경사항을 저장하시겠습니까?",
    "취소하기", "취소하시겠습니까?", "작업을 취소하시겠습니까?",
    "삭제하기", "삭제하시겠습니까?", "선택한 항목을 삭제하시겠습니까?",
    "확인", "확인하시겠습니까?", "계속 진행하시겠습니까?",
    "로그인", "로그인하기", "로그인에 성공했습니다", "로그인에 실패했습니다",
    "로그아웃", "로그아웃하시겠습니까?", "로그아웃되었습니다",
    "비밀번호", "비밀번호를 입력해 주세요", "비밀번호가 일치하지 않습니다",
    "패스워드", "패스워드 변경", "패스워드를 재설정합니다",
    "시작", "시작하기", "게임을 시작합니다", "작업을 시작합니다",
    "종료", "종료하기", "프로그램을 종료하시겠습니까?",
    "끝내기", "게임을 끝내시겠습니까?",
    "설정", "설정하기", "환경설정", "게임 설정", "시스템 설정",
    "파일", "파일 선택", "파일을 선택해 주세요", "파일 저장 완료",
    "폴더", "폴더 선택", "폴더를 생성하시겠습니까?",
    "오류", "오류가 발생했습니다", "에러", "에러가 발생했습니다",
    "성공", "작업이 완료되었습니다", "성공적으로 저장되었습니다",
    "실패", "작업에 실패했습니다", "저장에 실패했습니다",
    "네트워크", "네트워크 연결 오류", "인터넷 연결을 확인해 주세요",
    "서버", "서버에 연결할 수 없습니다", "서버 점검 중입니다",
    "업데이트", "업데이트가 있습니다", "업데이트를 진행하시겠습니까?",
    "다운로드", "다운로드 중입니다", "다운로드가 완료되었습니다",
    "게임", "게임 시작", "게임 종료", "게임을 일시정지합니다",
    "캐릭터", "캐릭터 선택", "캐릭터를 생성하시겠습니까?",
    "아이템", "아이템 획득", "아이템을 사용하시겠습니까?",
    "스킬", "스킬 사용", "스킬을 배우시겠습니까?",
    "퀘스트", "퀘스트 완료", "퀘스트를 수락하시겠습니까?",
    "인벤토리", "인벤토리가 가득 찼습니다", "인벤토리 정리",
    "상점", "상점 열기", "상점에서 구매하시겠습니까?",
    "구매", "구매하기", "구매하시겠습니까?", "구매가 완료되었습니다",
    "판매", "판매하기", "판매하시겠습니까?", "판매가 완료되었습니다",
    "레벨", "레벨 업", "레벨이 올랐습니다", "최대 레벨에 도달했습니다",
    "경험치", "경험치 획득", "경험치가 부족합니다",
    "골드", "골드 획득", "골드가 부족합니다",
    "보석", "보석 획득", "보석을 사용하시겠습니까?",
    "친구", "친구 추가", "친구 요청을 보내시겠습니까?",
    "길드", "길드 가입", "길드를 생성하시겠습니까?",
    "채팅", "채팅하기", "채팅이 차단되었습니다",
    "메시지", "메시지 보내기", "새 메시지가 있습니다",
    "알림", "알림 설정", "새 알림이 있습니다",
    "보상", "보상 받기", "일일 보상을 받으시겠습니까?",
    "이벤트", "이벤트 참여", "이벤트가 종료되었습니다",
    "공지", "공지사항", "새 공지사항이 있습니다",
    "도움말", "도움말 보기", "자주 묻는 질문",
    "문의", "문의하기", "고객센터에 문의해 주세요",
]


def get_memory_mb() -> float:
    """Get current process memory in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def generate_tm_corpus(size: int = 5000) -> List[str]:
    """Generate TM corpus by repeating and varying base phrases."""
    import random
    random.seed(42)

    corpus = list(KOREAN_TM_CORPUS)

    # Add variations
    prefixes = ["", "게임: ", "[시스템] ", "알림: ", ""]
    suffixes = ["", ".", "!", "?", ""]

    while len(corpus) < size:
        base = random.choice(KOREAN_TM_CORPUS)
        prefix = random.choice(prefixes)
        suffix = random.choice(suffixes)
        corpus.append(f"{prefix}{base}{suffix}")

    return corpus[:size]


def generate_queries(count: int = 500) -> List[Tuple[str, str]]:
    """Generate test queries with expected matches."""
    import random
    random.seed(123)

    queries = []

    # Add semantic test pairs
    for query, expected, _ in SEMANTIC_TEST_PAIRS:
        queries.append((query, expected))

    # Add random corpus samples as self-match queries
    corpus = list(KOREAN_TM_CORPUS)
    while len(queries) < count:
        text = random.choice(corpus)
        # Use partial text as query
        if len(text) > 3:
            partial = text[:len(text)//2] if random.random() > 0.5 else text
            queries.append((partial, text))

    return queries[:count]


class Model2VecSearcher:
    """Model2Vec-based semantic search."""

    def __init__(self):
        self.model = None
        self.corpus = []
        self.embeddings = None
        self.load_time = 0
        self.index_time = 0

    def load_model(self):
        """Load Model2Vec multilingual model."""
        from model2vec import StaticModel

        print("  Loading Model2Vec (potion-multilingual-128M)...")
        start = time.time()
        self.model = StaticModel.from_pretrained("minishlab/potion-multilingual-128M")
        self.load_time = time.time() - start
        print(f"  Model loaded in {self.load_time:.2f}s")

    def build_index(self, corpus: List[str]):
        """Build embeddings for corpus."""
        self.corpus = corpus

        print(f"  Building embeddings for {len(corpus)} entries...")
        start = time.time()
        self.embeddings = self.model.encode(corpus)
        self.index_time = time.time() - start
        print(f"  Index built in {self.index_time:.2f}s")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar texts."""
        query_emb = self.model.encode([query])

        # Cosine similarity
        similarities = np.dot(self.embeddings, query_emb.T).flatten()

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((self.corpus[idx], float(similarities[idx])))

        return results

    def batch_search(self, queries: List[str], top_k: int = 5) -> Tuple[List[List[Tuple[str, float]]], float]:
        """Batch search with timing."""
        start = time.time()

        # Encode all queries at once
        query_embs = self.model.encode(queries)

        # Compute all similarities
        all_similarities = np.dot(query_embs, self.embeddings.T)

        results = []
        for i, similarities in enumerate(all_similarities):
            top_indices = np.argsort(similarities)[::-1][:top_k]
            result = [(self.corpus[idx], float(similarities[idx])) for idx in top_indices]
            results.append(result)

        elapsed = time.time() - start
        return results, elapsed


class QwenSearcher:
    """Qwen-based semantic search."""

    def __init__(self):
        self.model = None
        self.corpus = []
        self.embeddings = None
        self.load_time = 0
        self.index_time = 0

    def load_model(self):
        """Load Qwen embedding model."""
        from sentence_transformers import SentenceTransformer
        import torch

        print("  Loading Qwen (Qwen3-Embedding-0.6B)...")
        start = time.time()
        self.model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.load_time = time.time() - start
        print(f"  Model loaded in {self.load_time:.2f}s (device: {self.device})")

    def build_index(self, corpus: List[str]):
        """Build embeddings for corpus."""
        self.corpus = corpus

        print(f"  Building embeddings for {len(corpus)} entries...")
        start = time.time()
        self.embeddings = self.model.encode(corpus, device=self.device, show_progress_bar=True)
        self.index_time = time.time() - start
        print(f"  Index built in {self.index_time:.2f}s")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar texts."""
        query_emb = self.model.encode([query], device=self.device)

        # Cosine similarity
        similarities = np.dot(self.embeddings, query_emb.T).flatten()

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((self.corpus[idx], float(similarities[idx])))

        return results

    def batch_search(self, queries: List[str], top_k: int = 5) -> Tuple[List[List[Tuple[str, float]]], float]:
        """Batch search with timing."""
        start = time.time()

        # Encode all queries at once
        query_embs = self.model.encode(queries, device=self.device)

        # Compute all similarities
        all_similarities = np.dot(query_embs, self.embeddings.T)

        results = []
        for i, similarities in enumerate(all_similarities):
            top_indices = np.argsort(similarities)[::-1][:top_k]
            result = [(self.corpus[idx], float(similarities[idx])) for idx in top_indices]
            results.append(result)

        elapsed = time.time() - start
        return results, elapsed


def evaluate_semantic_quality(searcher, name: str) -> Dict[str, Any]:
    """Evaluate semantic matching quality."""
    print(f"\n  {name} - Semantic Quality Test:")
    print("  " + "-" * 50)

    correct = 0
    total = len(SEMANTIC_TEST_PAIRS)
    details = []

    for query, expected, desc in SEMANTIC_TEST_PAIRS:
        results = searcher.search(query, top_k=5)

        # Check if expected is in top 5
        found = any(expected in r[0] or r[0] in expected for r, _ in [(r, None) for r in results])
        top_match = results[0][0] if results else "N/A"
        top_score = results[0][1] if results else 0

        if found:
            correct += 1
            status = "✓"
        else:
            status = "✗"

        details.append({
            "query": query,
            "expected": expected,
            "top_match": top_match,
            "score": top_score,
            "found": found,
            "desc": desc
        })

        print(f"  {status} '{query}' → '{top_match}' ({top_score:.3f}) [expect: '{expected}']")

    accuracy = correct / total * 100
    print(f"\n  Accuracy: {correct}/{total} ({accuracy:.1f}%)")

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "details": details
    }


def run_benchmark():
    """Run full benchmark."""
    print("=" * 70)
    print("MODEL2VEC vs QWEN BENCHMARK")
    print("=" * 70)

    # Configuration
    CORPUS_SIZE = 5000
    QUERY_COUNT = 500

    print(f"\nConfiguration:")
    print(f"  Corpus size: {CORPUS_SIZE}")
    print(f"  Query count: {QUERY_COUNT}")
    print(f"  Initial memory: {get_memory_mb():.1f} MB")

    # Generate data
    print("\n" + "=" * 70)
    print("GENERATING TEST DATA")
    print("=" * 70)

    corpus = generate_tm_corpus(CORPUS_SIZE)
    queries = generate_queries(QUERY_COUNT)
    query_texts = [q[0] for q in queries]

    print(f"  Corpus: {len(corpus)} entries")
    print(f"  Queries: {len(queries)} queries")
    print(f"  Sample corpus: {corpus[:3]}")
    print(f"  Sample queries: {[q[0] for q in queries[:3]]}")

    results = {}

    # =========================================
    # MODEL2VEC BENCHMARK
    # =========================================
    print("\n" + "=" * 70)
    print("MODEL2VEC BENCHMARK")
    print("=" * 70)

    gc.collect()
    mem_before = get_memory_mb()

    m2v = Model2VecSearcher()

    try:
        m2v.load_model()
        mem_after_load = get_memory_mb()

        m2v.build_index(corpus)
        mem_after_index = get_memory_mb()

        # Batch search
        print(f"\n  Running {QUERY_COUNT} queries...")
        m2v_results, m2v_search_time = m2v.batch_search(query_texts, top_k=5)

        # Semantic quality
        m2v_quality = evaluate_semantic_quality(m2v, "Model2Vec")

        results["model2vec"] = {
            "load_time": m2v.load_time,
            "index_time": m2v.index_time,
            "search_time": m2v_search_time,
            "queries_per_sec": QUERY_COUNT / m2v_search_time,
            "memory_model": mem_after_load - mem_before,
            "memory_index": mem_after_index - mem_after_load,
            "memory_total": mem_after_index - mem_before,
            "quality": m2v_quality
        }

        print(f"\n  Model2Vec Results:")
        print(f"    Load time: {m2v.load_time:.2f}s")
        print(f"    Index time: {m2v.index_time:.2f}s")
        print(f"    Search time ({QUERY_COUNT} queries): {m2v_search_time:.3f}s")
        print(f"    Queries/sec: {QUERY_COUNT / m2v_search_time:,.0f}")
        print(f"    Memory (model): {mem_after_load - mem_before:.1f} MB")
        print(f"    Memory (total): {mem_after_index - mem_before:.1f} MB")
        print(f"    Semantic accuracy: {m2v_quality['accuracy']:.1f}%")

    except Exception as e:
        print(f"  [ERROR] Model2Vec failed: {e}")
        results["model2vec"] = {"error": str(e)}

    # Clean up
    del m2v
    gc.collect()

    # =========================================
    # QWEN BENCHMARK
    # =========================================
    print("\n" + "=" * 70)
    print("QWEN BENCHMARK")
    print("=" * 70)

    gc.collect()
    mem_before = get_memory_mb()

    qwen = QwenSearcher()

    try:
        qwen.load_model()
        mem_after_load = get_memory_mb()

        qwen.build_index(corpus)
        mem_after_index = get_memory_mb()

        # Batch search
        print(f"\n  Running {QUERY_COUNT} queries...")
        qwen_results, qwen_search_time = qwen.batch_search(query_texts, top_k=5)

        # Semantic quality
        qwen_quality = evaluate_semantic_quality(qwen, "Qwen")

        results["qwen"] = {
            "load_time": qwen.load_time,
            "index_time": qwen.index_time,
            "search_time": qwen_search_time,
            "queries_per_sec": QUERY_COUNT / qwen_search_time,
            "memory_model": mem_after_load - mem_before,
            "memory_index": mem_after_index - mem_after_load,
            "memory_total": mem_after_index - mem_before,
            "quality": qwen_quality
        }

        print(f"\n  Qwen Results:")
        print(f"    Load time: {qwen.load_time:.2f}s")
        print(f"    Index time: {qwen.index_time:.2f}s")
        print(f"    Search time ({QUERY_COUNT} queries): {qwen_search_time:.3f}s")
        print(f"    Queries/sec: {QUERY_COUNT / qwen_search_time:,.0f}")
        print(f"    Memory (model): {mem_after_load - mem_before:.1f} MB")
        print(f"    Memory (total): {mem_after_index - mem_before:.1f} MB")
        print(f"    Semantic accuracy: {qwen_quality['accuracy']:.1f}%")

    except Exception as e:
        print(f"  [ERROR] Qwen failed: {e}")
        results["qwen"] = {"error": str(e)}

    # =========================================
    # COMPARISON SUMMARY
    # =========================================
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)

    if "error" not in results.get("model2vec", {}) and "error" not in results.get("qwen", {}):
        m2v = results["model2vec"]
        qw = results["qwen"]

        print(f"""
┌─────────────────────┬─────────────────┬─────────────────┬──────────────┐
│ Metric              │ Model2Vec       │ Qwen            │ Winner       │
├─────────────────────┼─────────────────┼─────────────────┼──────────────┤
│ Load Time           │ {m2v['load_time']:>10.2f}s     │ {qw['load_time']:>10.2f}s     │ {'Model2Vec' if m2v['load_time'] < qw['load_time'] else 'Qwen':^12} │
│ Index Time          │ {m2v['index_time']:>10.2f}s     │ {qw['index_time']:>10.2f}s     │ {'Model2Vec' if m2v['index_time'] < qw['index_time'] else 'Qwen':^12} │
│ Search Time         │ {m2v['search_time']:>10.3f}s     │ {qw['search_time']:>10.3f}s     │ {'Model2Vec' if m2v['search_time'] < qw['search_time'] else 'Qwen':^12} │
│ Queries/sec         │ {m2v['queries_per_sec']:>10,.0f}       │ {qw['queries_per_sec']:>10,.0f}       │ {'Model2Vec' if m2v['queries_per_sec'] > qw['queries_per_sec'] else 'Qwen':^12} │
│ Memory (Total)      │ {m2v['memory_total']:>10.1f} MB   │ {qw['memory_total']:>10.1f} MB   │ {'Model2Vec' if m2v['memory_total'] < qw['memory_total'] else 'Qwen':^12} │
│ Semantic Accuracy   │ {m2v['quality']['accuracy']:>10.1f}%     │ {qw['quality']['accuracy']:>10.1f}%     │ {'Model2Vec' if m2v['quality']['accuracy'] > qw['quality']['accuracy'] else 'Qwen':^12} │
└─────────────────────┴─────────────────┴─────────────────┴──────────────┘

Speed Ratio: Model2Vec is {qw['search_time']/m2v['search_time']:.1f}x faster
Memory Ratio: Model2Vec uses {m2v['memory_total']/qw['memory_total']*100:.1f}% of Qwen's memory
Quality Gap: {abs(m2v['quality']['accuracy'] - qw['quality']['accuracy']):.1f}% difference
""")

        # Recommendation
        print("RECOMMENDATION:")
        if m2v['quality']['accuracy'] >= qw['quality']['accuracy'] * 0.85:
            print("  → Model2Vec is viable as DEFAULT (85%+ quality with massive speed gain)")
        else:
            print("  → Model2Vec quality may be too low for production use")

        if m2v['quality']['accuracy'] >= 70:
            print("  → Model2Vec suitable for: typo tolerance, near-matches, fast previews")

        print("  → Qwen suitable for: maximum accuracy, synonym matching, final lookup")

    return results


if __name__ == "__main__":
    results = run_benchmark()
    sys.exit(0 if results else 1)
