# Data Preprocessing & Deduplication

**Source:** `~/WebTranslatorNew/app/services/glossary/preprocessor.py`

---

## Preprocessing Pipeline

```
Raw Data (Excel, etc)
    ↓
1. Remove Empty Cells
    ↓
2. Clean Control Characters
    ↓
3. Resolve Duplicates (majority voting)
    ↓
4. Filter Database Duplicates (PREPROCESS)
    ↓
Cleaned Data → Embedding Pipeline
```

---

## Data Preprocessor Class

```python
class DataPreprocessor:
    def preprocess_data(
        self,
        data: List[Dict],
        glossary_id: int = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Clean and deduplicate data.

        Returns:
            cleaned_data: DataFrame ready for embedding
            stats: {
                'empty_cells_removed': N,
                'duplicates_resolved': N,
                'db_duplicates_filtered': N
            }
        """
```

---

## Step 1: Remove Empty Cells

```python
def _remove_empty_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with blank source or target"""
    return df.dropna(subset=['source', 'target'])
```

---

## Step 2: Clean Control Characters

```python
def _clean_control_characters(df: pd.DataFrame) -> pd.DataFrame:
    """Remove Excel artifacts and excess whitespace"""
    for col in ['source', 'target']:
        df[col] = df[col].str.replace('_x000D_', '', regex=False)
        df[col] = df[col].str.strip()
    return df
```

---

## Step 3: Resolve Duplicates (Majority Voting)

```python
from collections import Counter

def _resolve_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each source text with multiple translations,
    keep the MOST FREQUENT target translation.
    """
    source_counts = df['source'].value_counts()
    duplicated_sources = source_counts[source_counts > 1].index

    for source_text in duplicated_sources:
        dupes = df[df['source'] == source_text]

        # Count target translations
        target_counts = Counter(dupes['target'].tolist())

        # Select most frequent
        most_common_target, _ = target_counts.most_common(1)[0]

        # Keep only rows with most common target
        df = df[~((df['source'] == source_text) &
                  (df['target'] != most_common_target))]

    return df
```

**Strategy:** Majority voting on translations

---

## Step 4: Filter Database Duplicates

```python
def _filter_database_duplicates(
    df: pd.DataFrame,
    glossary_id: int
) -> pd.DataFrame:
    """
    PREPROCESS: Skip entries already in database.
    Saves embedding generation for duplicates!
    """
    existing_entries = GlossaryEntry.query.filter_by(
        glossary_id=glossary_id
    ).all()

    existing_pairs = {
        (entry.source_text.strip(), entry.target_text.strip())
        for entry in existing_entries
    }

    def is_not_duplicate(row):
        pair = (row['source_normalized'], row['target_normalized'])
        return pair not in existing_pairs

    return df[df.apply(is_not_duplicate, axis=1)]
```

**Optimization:** Prevents wasted embedding computation

---

## Line-Level Processing

### 1:1 Line Mapping Detection
```python
def should_create_line_entries(source_text: str, target_text: str) -> bool:
    """
    Create line entries only when:
    1. Multi-line entry (>1 line)
    2. Same number of lines in source and target
    3. Empty lines match (content-empty pairs align)
    """
    source_lines = source_text.split('\n')
    target_lines = target_text.split('\n')

    if len(source_lines) <= 1:
        return False

    if len(source_lines) != len(target_lines):
        return False

    # Verify 1:1 mapping
    for src_line, tgt_line in zip(source_lines, target_lines):
        src_has_content = bool(src_line.strip())
        tgt_has_content = bool(tgt_line.strip())
        if src_has_content != tgt_has_content:
            return False

    return True
```

### Create Line Entries
```python
def create_line_entries(entry_id: int, source_text: str, target_text: str):
    source_lines = source_text.split('\n')
    target_lines = target_text.split('\n')

    for line_num, (src, tgt) in enumerate(zip(source_lines, target_lines)):
        if src.strip() and tgt.strip():
            GlossaryLineEntry(
                entry_id=entry_id,
                line_number=line_num,
                source_line=src,
                target_line=tgt,
                embedding=generate_embedding(src)
            )
```

---

## Integration for LDM

```python
# Usage in LDM file import
preprocessor = DataPreprocessor()

cleaned_data, stats = preprocessor.preprocess_data(
    data=parsed_rows,
    glossary_id=ldm_file_id
)

logger.info(f"Preprocessing stats: {stats}")
# {'empty_cells_removed': 5, 'duplicates_resolved': 12, ...}

# Proceed with embedding generation for cleaned_data only
```

---

## Incremental Updates

From KR Similar (`server/tools/kr_similar/embeddings.py:232-309`):

```python
def update_embeddings_incremental(
    existing_embeddings: np.ndarray,
    existing_dict: dict,
    new_data: pd.DataFrame
):
    """
    Update embeddings without rebuilding from scratch.

    1. Load existing embeddings/dict
    2. Identify new or changed strings
    3. Generate embeddings only for new/changed
    4. Replace existing OR append new
    5. Save updated files
    """
    # Find new/changed
    new_or_changed = new_data[
        ~new_data['Korean'].isin(existing_dict.keys())
    ]

    # Generate only for new/changed
    new_embeddings = model.encode(new_or_changed['Korean'].tolist())

    # Update: replace or append
    for i, korean_text in enumerate(new_or_changed['Korean']):
        if korean_text in korean_to_idx:
            # Replace existing
            updated_embeddings[korean_to_idx[korean_text]] = new_embeddings[i]
        else:
            # Append new
            updated_embeddings = np.vstack([updated_embeddings, [new_embeddings[i]]])
            updated_dict[korean_text] = translation

    return updated_embeddings, updated_dict
```
