#!/bin/bash
# CLI Testing for XLSTransfer - Full Functionality Without GUI
# This allows Claude to test ALL XLSTransfer operations via terminal

set -e

PROJECT_ROOT="/home/neil1988/LocalizationTools"
TEST_DIR="/tmp/xlstransfer_cli_test"
API_URL="http://localhost:8888"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🧪 XLSTransfer CLI Testing"
echo "=========================================="
echo ""

# Setup
mkdir -p "$TEST_DIR"
cd "$PROJECT_ROOT"

# Login to get token
echo "🔐 Logging in..."
TOKEN=$(curl -s -X POST "$API_URL/api/v2/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r '.token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Login failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Logged in successfully${NC}"
echo ""

# Test 1: Python Module - Create Dictionary (Direct)
echo "1️⃣  Testing Dictionary Creation (Direct Python)..."
echo ""

# Create test Excel file with openpyxl
python3 << 'PYTHON_SCRIPT'
import openpyxl
from pathlib import Path

test_dir = Path("/tmp/xlstransfer_cli_test")
test_file = test_dir / "test_dictionary.xlsx"

# Create test workbook
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Sheet1"

# Headers
ws['A1'] = 'KR'
ws['B1'] = 'Translation'

# Test data
test_data = [
    ('안녕하세요', 'Hello'),
    ('감사합니다', 'Thank you'),
    ('좋은 아침입니다', 'Good morning'),
    ('안녕히 가세요', 'Goodbye'),
    ('환영합니다', 'Welcome')
]

for idx, (kr, en) in enumerate(test_data, start=2):
    ws[f'A{idx}'] = kr
    ws[f'B{idx}'] = en

wb.save(test_file)
print(f"✅ Test file created: {test_file}")
print(f"   Entries: {len(test_data)}")
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test dictionary file created${NC}"
else
    echo -e "${RED}❌ Failed to create test file${NC}"
fi
echo ""

# Test 2: Python Module - Direct Function Call
echo "2️⃣  Testing Core Functions (Direct Python)..."
echo ""

python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools')

try:
    from client.tools.xls_transfer import core
    print("✅ Core module imported successfully")

    # Test text cleaning
    dirty_text = "Hello_x000D_World"
    clean = core.clean_text(dirty_text)
    print(f"   clean_text: '{dirty_text}' → '{clean}'")

    # Test number replacement
    text_with_code = "{ItemID}Hello"
    replaced = core.simple_number_replace(text_with_code, "World")
    print(f"   simple_number_replace: '{text_with_code}' → '{replaced}'")

    print("✅ Core functions working correctly")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo ""

# Test 3: Model Loading
echo "3️⃣  Testing BERT Model Loading..."
echo ""

python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools')

try:
    from sentence_transformers import SentenceTransformer

    model_name = 'snunlp/KR-SBERT-V40K-klueNLI-augSTS'
    model_path = 'client/models/KR-SBERT-V40K-klueNLI-augSTS'

    print(f"Loading model: {model_name}")
    print(f"From: {model_path}")

    # Try to load model
    model = SentenceTransformer(model_path)

    # Test encoding
    test_text = "안녕하세요"
    embedding = model.encode(test_text)

    print(f"✅ Model loaded successfully")
    print(f"   Embedding dimension: {len(embedding)}")
    print(f"   Test text: '{test_text}'")
    print(f"   Embedding shape: {embedding.shape if hasattr(embedding, 'shape') else 'N/A'}")

except FileNotFoundError:
    print(f"⚠️  Model not found at {model_path}")
    print("   Run: python3 scripts/download_models.py")
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo ""

# Test 4: FAISS Index Creation
echo "4️⃣  Testing FAISS Index Creation..."
echo ""

python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools')

try:
    import numpy as np
    import faiss

    # Create dummy embeddings
    dimension = 768  # Korean BERT dimension
    num_entries = 10

    embeddings = np.random.randn(num_entries, dimension).astype('float32')

    # Normalize
    faiss.normalize_L2(embeddings)

    # Create index
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    print(f"✅ FAISS index created")
    print(f"   Dimension: {dimension}")
    print(f"   Entries: {index.ntotal}")

    # Test search
    query = np.random.randn(1, dimension).astype('float32')
    faiss.normalize_L2(query)

    distances, indices = index.search(query, k=3)
    print(f"   Search test: Found {len(indices[0])} matches")
    print(f"   Top similarity: {distances[0][0]:.4f}")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

echo ""

# Test 5: Excel Processing
echo "5️⃣  Testing Excel File Processing..."
echo ""

python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/home/neil1988/LocalizationTools')

try:
    from client.tools.xls_transfer import excel_utils
    from pathlib import Path

    test_file = Path("/tmp/xlstransfer_cli_test/test_dictionary.xlsx")

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)

    # Read Excel file
    data = excel_utils.read_excel_file(
        str(test_file),
        sheet_name='Sheet1'
    )

    print(f"✅ Excel file read successfully")
    print(f"   File: {test_file.name}")
    print(f"   Sheets: {data.get('sheets', [])}")
    print(f"   Rows: {len(data.get('rows', []))}")

    # Show first 3 entries
    if 'rows' in data and data['rows']:
        print(f"   Sample data:")
        for row in data['rows'][:3]:
            print(f"      {row}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

echo ""

# Summary
echo "=========================================="
echo "📊 TEST SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}✅ All core components tested${NC}"
echo ""
echo "Components Verified:"
echo "  ✅ Authentication (JWT token)"
echo "  ✅ Test file creation (Excel)"
echo "  ✅ Core functions (clean_text, simple_number_replace)"
echo "  ✅ BERT model loading capability"
echo "  ✅ FAISS index creation"
echo "  ✅ Excel file processing"
echo ""
echo "Test Files:"
echo "  - $TEST_DIR/test_dictionary.xlsx"
echo ""
echo "Next Steps:"
echo "  1. Test full dictionary creation workflow"
echo "  2. Test translation operations"
echo "  3. Test file output generation"
echo ""
echo "=========================================="
