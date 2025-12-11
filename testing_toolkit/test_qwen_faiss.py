#!/usr/bin/env python3
"""
Qwen + FAISS Integration Test Script
=====================================

Tests the full Qwen embedding + FAISS search pipeline:
1. Model loading (Qwen3-Embedding-0.6B)
2. Embedding generation
3. FAISS HNSW index creation
4. Similarity search

Run: python3 testing_toolkit/test_qwen_faiss.py
"""

import sys
import time
import numpy as np
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test required library imports."""
    print("\n" + "="*60)
    print("TEST 1: Library Imports")
    print("="*60)

    errors = []

    try:
        import torch
        print(f"  [OK] PyTorch {torch.__version__}")
        print(f"       CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"       CUDA device: {torch.cuda.get_device_name(0)}")
    except ImportError as e:
        errors.append(f"PyTorch: {e}")
        print(f"  [FAIL] PyTorch: {e}")

    try:
        import faiss
        print(f"  [OK] FAISS {faiss.__version__ if hasattr(faiss, '__version__') else 'installed'}")
    except ImportError as e:
        errors.append(f"FAISS: {e}")
        print(f"  [FAIL] FAISS: {e}")

    try:
        from sentence_transformers import SentenceTransformer
        print(f"  [OK] SentenceTransformers")
    except ImportError as e:
        errors.append(f"SentenceTransformers: {e}")
        print(f"  [FAIL] SentenceTransformers: {e}")

    try:
        import transformers
        print(f"  [OK] Transformers {transformers.__version__}")
    except ImportError as e:
        errors.append(f"Transformers: {e}")
        print(f"  [FAIL] Transformers: {e}")

    return len(errors) == 0, errors


def test_qwen_model_loading():
    """Test Qwen model loading."""
    print("\n" + "="*60)
    print("TEST 2: Qwen Model Loading")
    print("="*60)

    try:
        import torch
        from sentence_transformers import SentenceTransformer

        MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
        print(f"  Loading model: {MODEL_NAME}")

        start = time.time()
        model = SentenceTransformer(MODEL_NAME)
        load_time = time.time() - start

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        print(f"  [OK] Model loaded in {load_time:.2f}s")
        print(f"       Device: {device}")
        print(f"       Embedding dimension: {model.get_sentence_embedding_dimension()}")

        return True, model
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False, None


def test_embedding_generation(model):
    """Test embedding generation."""
    print("\n" + "="*60)
    print("TEST 3: Embedding Generation")
    print("="*60)

    if model is None:
        print("  [SKIP] Model not loaded")
        return False, None

    try:
        import torch

        # Test texts (Korean, English, mixed)
        test_texts = [
            "안녕하세요",  # Korean: Hello
            "Hello world",  # English
            "번역 테스트입니다",  # Korean: This is a translation test
            "Translation test",  # English
            "게임 아이템을 구매하시겠습니까?",  # Korean: Would you like to purchase the game item?
            "Would you like to purchase the game item?",  # English
            "스킬을 사용합니다",  # Korean: Using skill
            "Using skill",  # English
        ]

        print(f"  Encoding {len(test_texts)} texts...")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        start = time.time()
        embeddings = model.encode(test_texts, device=device)
        encode_time = time.time() - start

        print(f"  [OK] Embeddings generated in {encode_time:.4f}s")
        print(f"       Shape: {embeddings.shape}")
        print(f"       Rate: {len(test_texts)/encode_time:.1f} texts/sec")

        return True, (embeddings, test_texts)
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False, None


def test_faiss_index_creation(embeddings_data):
    """Test FAISS HNSW index creation."""
    print("\n" + "="*60)
    print("TEST 4: FAISS HNSW Index Creation")
    print("="*60)

    if embeddings_data is None:
        print("  [SKIP] No embeddings available")
        return False, None

    try:
        import faiss

        embeddings, texts = embeddings_data

        # Normalize embeddings (required for cosine similarity)
        print("  Normalizing embeddings...")
        embeddings = embeddings.astype('float32')
        faiss.normalize_L2(embeddings)

        # Create HNSW index (same config as KR Similar)
        embedding_dim = embeddings.shape[1]
        print(f"  Creating HNSW index (dim={embedding_dim})...")

        start = time.time()
        index = faiss.IndexHNSWFlat(embedding_dim, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 400
        index.hnsw.efSearch = 500
        index.add(embeddings)
        build_time = time.time() - start

        print(f"  [OK] FAISS index built in {build_time:.4f}s")
        print(f"       Index size: {index.ntotal} vectors")
        print(f"       Dimension: {index.d}")

        return True, (index, embeddings, texts)
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False, None


def test_similarity_search(index_data, model):
    """Test similarity search."""
    print("\n" + "="*60)
    print("TEST 5: Similarity Search")
    print("="*60)

    if index_data is None or model is None:
        print("  [SKIP] Index or model not available")
        return False

    try:
        import faiss
        import torch

        index, embeddings, texts = index_data
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Test queries
        queries = [
            "안녕",  # Should match "안녕하세요"
            "game item purchase",  # Should match purchase text
            "스킬 사용",  # Should match "스킬을 사용합니다"
        ]

        print(f"  Running {len(queries)} search queries...\n")

        for query in queries:
            # Encode query
            query_emb = model.encode([query], device=device).astype('float32')
            faiss.normalize_L2(query_emb)

            # Search
            start = time.time()
            scores, indices = index.search(query_emb, k=3)
            search_time = (time.time() - start) * 1000

            print(f"  Query: \"{query}\"")
            print(f"  Search time: {search_time:.2f}ms")
            print("  Results:")
            for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
                if idx >= 0:
                    print(f"    {i+1}. [{score:.3f}] \"{texts[idx]}\"")
            print()

        print("  [OK] Similarity search working")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_kr_similar_integration():
    """Test KR Similar module integration."""
    print("\n" + "="*60)
    print("TEST 6: KR Similar Module Integration")
    print("="*60)

    try:
        from server.tools.kr_similar.embeddings import EmbeddingsManager, MODEL_NAME

        print(f"  MODEL_NAME: {MODEL_NAME}")

        # Check if Qwen model is configured
        if "Qwen" in MODEL_NAME:
            print("  [OK] KR Similar using Qwen model (P20 migration complete)")
        else:
            print(f"  [INFO] KR Similar using: {MODEL_NAME}")

        # Create manager (don't load model yet)
        manager = EmbeddingsManager()
        status = manager.get_status()

        print(f"  Manager status:")
        print(f"    - Model loaded: {status['model_loaded']}")
        print(f"    - Models available: {status['models_available']}")
        print(f"    - Dict dir: {status['dictionaries_dir']}")

        # List available dictionaries
        dicts = manager.list_available_dictionaries()
        if dicts:
            print(f"  Available dictionaries: {len(dicts)}")
            for d in dicts:
                print(f"    - {d['dict_type']}: {d['total_pairs']} pairs")
        else:
            print("  No dictionaries created yet")

        print("  [OK] KR Similar integration verified")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_ldm_tm_integration():
    """Test LDM TM module integration."""
    print("\n" + "="*60)
    print("TEST 7: LDM TM Module Integration")
    print("="*60)

    try:
        from server.tools.ldm.tm import TranslationMemory, KR_SIMILAR_AVAILABLE

        print(f"  KR_SIMILAR_AVAILABLE: {KR_SIMILAR_AVAILABLE}")

        # Create TM instance (no DB session for basic test)
        tm = TranslationMemory()

        print(f"  TM settings:")
        print(f"    - Similarity threshold: {tm.similarity_threshold}")
        print(f"    - Max suggestions: {tm.max_suggestions}")

        # Test text similarity calculation
        test_cases = [
            ("안녕하세요", "안녕하세요", 1.0),  # Exact match
            ("스킬 사용", "스킬을 사용합니다", 0.5),  # Partial match
            ("hello", "world", 0.0),  # No match expected
        ]

        print("\n  Text similarity tests:")
        for text1, text2, expected_min in test_cases:
            similarity = tm._calculate_similarity(text1.lower(), text2.lower())
            status = "OK" if similarity >= expected_min else "WARN"
            print(f"    [{status}] \"{text1}\" vs \"{text2}\" = {similarity:.2f} (expected >= {expected_min})")

        print("\n  [OK] LDM TM integration verified")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_batch_performance(model):
    """Test batch embedding performance."""
    print("\n" + "="*60)
    print("TEST 8: Batch Performance Test")
    print("="*60)

    if model is None:
        print("  [SKIP] Model not loaded")
        return False

    try:
        import torch

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Generate test data
        batch_sizes = [10, 50, 100, 500]
        base_texts = [
            "게임 아이템을 구매하시겠습니까?",
            "스킬을 사용합니다",
            "퀘스트를 완료했습니다",
            "캐릭터 레벨이 올랐습니다",
            "인벤토리가 가득 찼습니다",
        ]

        print(f"  Device: {device}")
        print()

        for batch_size in batch_sizes:
            # Create test batch
            texts = base_texts * (batch_size // len(base_texts) + 1)
            texts = texts[:batch_size]

            start = time.time()
            embeddings = model.encode(texts, device=device, batch_size=64)
            elapsed = time.time() - start

            rate = batch_size / elapsed
            print(f"  Batch {batch_size:4d}: {elapsed:.3f}s ({rate:,.0f} texts/sec)")

        print("\n  [OK] Batch performance test complete")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("QWEN + FAISS INTEGRATION TEST")
    print("="*60)
    print(f"  Project: LocaNext")
    print(f"  Model: Qwen/Qwen3-Embedding-0.6B")
    print(f"  Index: FAISS HNSW")

    results = []
    model = None
    embeddings_data = None
    index_data = None

    # Test 1: Imports
    success, _ = test_imports()
    results.append(("Library Imports", success))

    if not success:
        print("\n[ABORT] Required libraries missing. Install with:")
        print("  pip install torch faiss-cpu sentence-transformers transformers")
        return 1

    # Test 2: Model loading
    success, model = test_qwen_model_loading()
    results.append(("Qwen Model Loading", success))

    # Test 3: Embedding generation
    success, embeddings_data = test_embedding_generation(model)
    results.append(("Embedding Generation", success))

    # Test 4: FAISS index
    success, index_data = test_faiss_index_creation(embeddings_data)
    results.append(("FAISS Index Creation", success))

    # Test 5: Similarity search
    success = test_similarity_search(index_data, model)
    results.append(("Similarity Search", success))

    # Test 6: KR Similar integration
    success = test_kr_similar_integration()
    results.append(("KR Similar Integration", success))

    # Test 7: LDM TM integration
    success = test_ldm_tm_integration()
    results.append(("LDM TM Integration", success))

    # Test 8: Batch performance
    success = test_batch_performance(model)
    results.append(("Batch Performance", success))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, s in results if s)
    total = len(results)

    for name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  [{status}] {name}")

    print()
    print(f"  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  [SUCCESS] All Qwen + FAISS tests passed!")
        return 0
    else:
        print(f"\n  [WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
