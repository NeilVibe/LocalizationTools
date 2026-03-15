<script>
  /**
   * CategoryFilter -- Multi-select category filter for translation grid.
   *
   * Phase 16 Plan 01: Category Clustering
   *
   * Uses Carbon MultiSelect to allow filtering rows by content categories
   * (Item, Character, Quest, Skill, Region, Gimmick, Knowledge, UI, Other).
   */
  import { MultiSelect } from "carbon-components-svelte";

  // Props (Svelte 5 runes)
  let { selectedCategories = $bindable([]), onchange = () => {} } = $props();

  // Category color mapping (LDE color scheme)
  const CATEGORY_COLORS = {
    "Item": "#D9D2E9",
    "Character": "#F8CBAD",
    "Quest": "#D9D2E9",
    "Skill": "#D9D2E9",
    "Region": "#F8CBAD",
    "Gimmick": "#D9D2E9",
    "Knowledge": "#D9D2E9",
    "UI": "#A9D08E",
    "Other": "#D9D9D9",
    "Uncategorized": "#D9D9D9",
  };

  // Category options for MultiSelect
  const categoryItems = [
    { id: "Item", text: "Item" },
    { id: "Character", text: "Character" },
    { id: "Quest", text: "Quest" },
    { id: "Skill", text: "Skill" },
    { id: "Region", text: "Region" },
    { id: "Gimmick", text: "Gimmick" },
    { id: "Knowledge", text: "Knowledge" },
    { id: "UI", text: "UI" },
    { id: "Other", text: "Other" },
  ];

  function handleSelect(e) {
    selectedCategories = e.detail.selectedIds;
    onchange(selectedCategories);
  }

  export { CATEGORY_COLORS };
</script>

<div class="category-filter">
  <MultiSelect
    size="sm"
    titleText=""
    hideLabel
    label="Category"
    items={categoryItems}
    selectedIds={selectedCategories}
    on:select={handleSelect}
    sortItem={(a, b) => a.text.localeCompare(b.text)}
  />
</div>

<style>
  .category-filter {
    min-width: 140px;
    max-width: 220px;
  }

  .category-filter :global(.bx--multi-select) {
    min-height: 2rem;
  }

  .category-filter :global(.bx--list-box__label) {
    font-size: 0.75rem;
  }
</style>
