<script>
  import {
    Modal,
    FileUploader,
    ProgressBar,
    InlineNotification,
    TextInput,
    Select,
    SelectItem,
    TextArea
  } from "carbon-components-svelte";
  import {
    Upload,
    CheckmarkFilled,
    WarningAlt
  } from "carbon-icons-svelte";
  import { createEventDispatcher } from "svelte";
  import { logger } from "$lib/utils/logger.js";

  const dispatch = createEventDispatcher();

  // API base URL
  const API_BASE = 'http://localhost:8888';

  // Svelte 5: Props
  let { open = $bindable(false) } = $props();

  // Svelte 5: Form state
  let tmName = $state("");
  let sourceLang = $state("ko");
  let targetLang = $state("en");
  let description = $state("");
  let uploadFiles = $state([]);

  // Svelte 5: Upload state
  let uploadStatus = $state(""); // '', 'uploading', 'success', 'error'
  let uploadProgress = $state(0);
  let errorMessage = $state("");
  let uploadResult = $state(null);

  // Languages
  const languages = [
    { value: "ko", label: "Korean (KO)" },
    { value: "en", label: "English (EN)" },
    { value: "ja", label: "Japanese (JA)" },
    { value: "zh", label: "Chinese (ZH)" },
    { value: "de", label: "German (DE)" },
    { value: "fr", label: "French (FR)" },
    { value: "es", label: "Spanish (ES)" },
    { value: "pt", label: "Portuguese (PT)" },
    { value: "ru", label: "Russian (RU)" },
    { value: "it", label: "Italian (IT)" },
    { value: "th", label: "Thai (TH)" },
    { value: "vi", label: "Vietnamese (VI)" },
    { value: "id", label: "Indonesian (ID)" }
  ];

  // Helper to get auth headers
  function getAuthHeaders() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  // Reset form
  function resetForm() {
    tmName = "";
    sourceLang = "ko";
    targetLang = "en";
    description = "";
    uploadFiles = [];
    uploadStatus = "";
    uploadProgress = 0;
    errorMessage = "";
    uploadResult = null;
  }

  // Upload TM
  async function uploadTM() {
    if (!uploadFiles.length || !tmName.trim()) {
      errorMessage = "Please provide a TM name and select a file";
      return;
    }

    const file = uploadFiles[0];
    uploadStatus = "uploading";
    uploadProgress = 10;
    errorMessage = "";

    try {
      const formData = new FormData();
      formData.append('name', tmName.trim());
      formData.append('source_lang', sourceLang);
      formData.append('target_lang', targetLang);
      if (description.trim()) {
        formData.append('description', description.trim());
      }
      formData.append('file', file);

      logger.info("Uploading TM", { name: tmName, file: file.name, size: file.size });

      // Simulate progress while uploading
      const progressInterval = setInterval(() => {
        if (uploadProgress < 90) {
          uploadProgress += 10;
        }
      }, 500);

      const response = await fetch(`${API_BASE}/api/ldm/tm/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      clearInterval(progressInterval);
      uploadProgress = 100;

      if (response.ok) {
        uploadResult = await response.json();
        uploadStatus = "success";
        logger.success("TM uploaded", {
          name: uploadResult.name,
          tmId: uploadResult.tm_id,
          entries: uploadResult.entry_count,
          rate: uploadResult.rate_per_second
        });

        // Dispatch event and close after delay
        setTimeout(() => {
          dispatch('uploaded', uploadResult);
          resetForm();
          open = false;
        }, 1500);

      } else {
        const error = await response.json();
        errorMessage = error.detail || "Upload failed";
        uploadStatus = "error";
        logger.error("TM upload failed", { error: errorMessage });
      }

    } catch (err) {
      errorMessage = err.message;
      uploadStatus = "error";
      logger.error("TM upload error", { error: err.message });
    }
  }

  // Handle modal close
  function handleClose() {
    if (uploadStatus !== "uploading") {
      resetForm();
      open = false;
    }
  }

  // Auto-generate TM name from file
  function handleFileAdd() {
    if (uploadFiles.length > 0 && !tmName) {
      const file = uploadFiles[0];
      tmName = file.name.replace(/\.[^.]+$/, '') + "_TM";
    }
  }

  // Svelte 5: Effect - Watch file changes
  $effect(() => {
    if (uploadFiles.length > 0) {
      handleFileAdd();
    }
  });
</script>

<Modal
  bind:open
  modalHeading="Upload Translation Memory"
  primaryButtonText={uploadStatus === "uploading" ? "Uploading..." : "Upload TM"}
  primaryButtonDisabled={uploadStatus === "uploading" || uploadStatus === "success"}
  secondaryButtonText="Cancel"
  on:click:button--primary={uploadTM}
  on:click:button--secondary={handleClose}
  on:close={handleClose}
>
  <div class="upload-form">
    {#if uploadStatus === "uploading"}
      <div class="upload-progress">
        <ProgressBar
          value={uploadProgress}
          max={100}
          labelText="Uploading and processing..."
          helperText="{uploadProgress}% complete"
        />
        <p class="progress-note">
          Large TM files may take a few moments to process.
        </p>
      </div>

    {:else if uploadStatus === "success" && uploadResult}
      <div class="upload-success">
        <CheckmarkFilled size={48} class="success-icon" />
        <h4>Upload Complete!</h4>
        <div class="success-details">
          <p><strong>{uploadResult.name}</strong></p>
          <p>{uploadResult.entry_count.toLocaleString()} entries imported</p>
          <p class="rate">({uploadResult.rate_per_second.toLocaleString()} entries/sec)</p>
        </div>
      </div>

    {:else if uploadStatus === "error"}
      <InlineNotification
        kind="error"
        title="Upload Failed"
        subtitle={errorMessage}
        on:close={() => { uploadStatus = ""; errorMessage = ""; }}
      />

      <div class="form-fields">
        <FileUploader
          labelTitle="Select TM file"
          labelDescription="Supported formats: TXT, TSV, XML, XLSX"
          buttonLabel="Add file"
          accept={[".txt", ".tsv", ".xml", ".xlsx", ".xls"]}
          bind:files={uploadFiles}
        />

        <TextInput
          bind:value={tmName}
          labelText="TM Name"
          placeholder="My Translation Memory"
          required
        />
      </div>

    {:else}
      <div class="form-fields">
        <FileUploader
          labelTitle="Select TM file"
          labelDescription="Supported: TXT (col 5→6), XML (StrOrigin→Str), XLSX (A→B)"
          buttonLabel="Add file"
          accept={[".txt", ".tsv", ".xml", ".xlsx", ".xls"]}
          bind:files={uploadFiles}
        />

        <TextInput
          bind:value={tmName}
          labelText="TM Name"
          placeholder="My Translation Memory"
          required
        />

        <div class="lang-row">
          <Select
            bind:selected={sourceLang}
            labelText="Source Language"
          >
            {#each languages as lang}
              <SelectItem value={lang.value} text={lang.label} />
            {/each}
          </Select>

          <span class="lang-arrow">→</span>

          <Select
            bind:selected={targetLang}
            labelText="Target Language"
          >
            {#each languages as lang}
              <SelectItem value={lang.value} text={lang.label} />
            {/each}
          </Select>
        </div>

        <TextArea
          bind:value={description}
          labelText="Description (Optional)"
          placeholder="Notes about this TM..."
          rows={2}
        />

        <div class="format-info">
          <h5>Format Guide:</h5>
          <ul>
            <li><strong>TXT/TSV:</strong> Column 5 = Source, Column 6 = Target</li>
            <li><strong>XML:</strong> StrOrigin = Source, Str = Target</li>
            <li><strong>XLSX:</strong> Column A = Source, Column B = Target</li>
          </ul>
        </div>
      </div>
    {/if}
  </div>
</Modal>

<style>
  .upload-form {
    min-height: 250px;
  }

  .form-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .lang-row {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
  }

  .lang-row :global(.bx--form-item) {
    flex: 1;
  }

  .lang-arrow {
    padding-bottom: 0.75rem;
    color: var(--cds-text-02);
    font-size: 1.25rem;
  }

  .format-info {
    margin-top: 0.5rem;
    padding: 0.75rem;
    background: var(--cds-layer-02);
    border-radius: 4px;
  }

  .format-info h5 {
    margin: 0 0 0.5rem 0;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--cds-text-01);
  }

  .format-info ul {
    margin: 0;
    padding-left: 1.25rem;
    font-size: 0.75rem;
    color: var(--cds-text-02);
  }

  .format-info li {
    margin: 0.25rem 0;
  }

  .upload-progress {
    padding: 2rem 0;
    text-align: center;
  }

  .progress-note {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: var(--cds-text-02);
  }

  .upload-success {
    padding: 2rem;
    text-align: center;
  }

  .upload-success :global(.success-icon) {
    color: var(--cds-support-success);
    margin-bottom: 1rem;
  }

  .upload-success h4 {
    margin: 0 0 1rem 0;
    color: var(--cds-text-01);
  }

  .success-details {
    color: var(--cds-text-02);
  }

  .success-details p {
    margin: 0.25rem 0;
  }

  .success-details .rate {
    font-size: 0.8125rem;
    color: var(--cds-text-03);
  }
</style>
