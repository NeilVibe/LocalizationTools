# Building Patched act_runner for Windows Cleanup Fix

**Purpose:** Fix the "Job Failed" false positive caused by Windows file locking during cleanup.

**Problem:** `os.RemoveAll()` fails on Windows because Go process holds file handles.

**Solution:** Patch the `Remove()` function to retry and ignore cleanup errors.

---

## Prerequisites

- Go 1.21+ installed
- Git installed
- Internet access to clone repos

---

## Step 1: Clone the Repositories

```bash
# Create work directory
mkdir -p ~/act_runner_patch && cd ~/act_runner_patch

# Clone act_runner (Gitea's runner)
git clone https://gitea.com/gitea/act_runner.git
cd act_runner

# Check current version
git describe --tags
```

---

## Step 2: Clone the act Library (Gitea's fork)

```bash
# Go back to work directory
cd ~/act_runner_patch

# Clone gitea's act fork
git clone https://gitea.com/gitea/act.git
cd act
```

---

## Step 3: Apply the Patch to act Library

Edit `pkg/container/host_environment.go`:

```bash
# Open the file
nano pkg/container/host_environment.go
```

Find the `Remove()` function (around line 150-160):

**BEFORE:**
```go
func (e *HostEnvironment) Remove() common.Executor {
	return func(_ context.Context) error {
		if e.CleanUp != nil {
			e.CleanUp()
		}
		return os.RemoveAll(e.Path)
	}
}
```

**AFTER (with fix):**
```go
func (e *HostEnvironment) Remove() common.Executor {
	return func(ctx context.Context) error {
		if e.CleanUp != nil {
			e.CleanUp()
		}

		// Windows cleanup fix: Retry with delays
		// File handles may still be held by the Go process
		var err error
		for i := 0; i < 5; i++ {
			err = os.RemoveAll(e.Path)
			if err == nil {
				return nil // Success
			}
			// Wait for handles to release (exponential backoff)
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Duration(i+1) * time.Second):
			}
		}

		// After 5 attempts, log warning but don't fail
		// The job already succeeded - cleanup failure is not critical
		if err != nil {
			// Log but don't return error - job status should stay "success"
			fmt.Fprintf(os.Stderr, "[WARN] Cleanup failed (non-fatal): %v\n", err)
		}
		return nil
	}
}
```

**Also add import at top if not present:**
```go
import (
	"fmt"
	"time"
	// ... other imports
)
```

---

## Step 4: Update act_runner to Use Local act

```bash
cd ~/act_runner_patch/act_runner

# Add replace directive to use local patched act
# Edit go.mod, add this line at the end:
echo 'replace gitea.com/gitea/act => ../act' >> go.mod

# Verify
cat go.mod | tail -5
```

---

## Step 5: Build for Windows

```bash
cd ~/act_runner_patch/act_runner

# Build for Windows AMD64
GOOS=windows GOARCH=amd64 go build -o act_runner.exe ./main.go

# Check the binary was created
ls -la act_runner.exe
```

---

## Step 6: Deploy to Windows Build Machine

```bash
# Copy to Windows (adjust path as needed)
cp act_runner.exe /mnt/c/NEIL_PROJECTS_WINDOWSBUILD/GiteaRunner/act_runner_patched.exe

# On Windows, backup old runner and replace:
# cd C:\NEIL_PROJECTS_WINDOWSBUILD\GiteaRunner
# ren act_runner.exe act_runner_original.exe
# ren act_runner_patched.exe act_runner.exe
```

---

## Step 7: Test

1. Trigger a Gitea build
2. Watch for `[WARN] Cleanup failed (non-fatal)` in logs
3. Check job status - should now show **SUCCESS** instead of failed

---

## Quick Patch Script

Save this as `apply_patch.sh`:

```bash
#!/bin/bash
cd ~/act_runner_patch/act

# Create patch file
cat > cleanup_fix.patch << 'EOF'
--- a/pkg/container/host_environment.go
+++ b/pkg/container/host_environment.go
@@ -1,6 +1,8 @@
 package container

 import (
+	"fmt"
+	"time"
 	"context"
 	"os"
 	// ... rest of imports
@@ -XX,XX +XX,XX @@ func (e *HostEnvironment) Remove() common.Executor {
-	return func(_ context.Context) error {
+	return func(ctx context.Context) error {
 		if e.CleanUp != nil {
 			e.CleanUp()
 		}
-		return os.RemoveAll(e.Path)
+
+		// Windows cleanup fix: Retry with delays
+		var err error
+		for i := 0; i < 5; i++ {
+			err = os.RemoveAll(e.Path)
+			if err == nil {
+				return nil
+			}
+			select {
+			case <-ctx.Done():
+				return ctx.Err()
+			case <-time.After(time.Duration(i+1) * time.Second):
+			}
+		}
+		if err != nil {
+			fmt.Fprintf(os.Stderr, "[WARN] Cleanup failed (non-fatal): %v\n", err)
+		}
+		return nil
 	}
 }
EOF

echo "Patch created. Apply manually due to line number variations."
```

---

## Expected Result

| Before Patch | After Patch |
|--------------|-------------|
| Job: FAILED | Job: SUCCESS |
| Cleanup error blocks status | Cleanup error logged but ignored |
| False positive failures | Accurate job status |

---

## Notes

- The fix tries 5 times with increasing delays (1s, 2s, 3s, 4s, 5s)
- After 5 attempts, it gives up but returns `nil` (success)
- Job status is preserved as SUCCESS
- Cleanup failure is logged as warning for visibility

---

*Created: 2025-12-09*
