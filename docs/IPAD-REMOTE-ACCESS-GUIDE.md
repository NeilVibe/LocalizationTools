# iPad Remote Access Guide

**Goal:** Access and control your Windows PC from your iPad, enabling mobile workflow with Claude.

**Recommended Solution:** Chrome Remote Desktop (simplest) or Tailscale + RDP (most secure)

---

## Why Chrome Remote Desktop?

| Criteria | Chrome Remote Desktop |
|----------|----------------------|
| Setup time | ~3 minutes |
| Cost | Free |
| Works through firewalls | Yes (no port forwarding needed) |
| iPad app | Yes (official, well-maintained) |
| Security | Google account + PIN |
| Performance | Good for general use |
| Reliability | Excellent |

It just works. No router configuration, no technical hurdles.

---

## Setup Instructions

### Part 1: Windows PC Setup

#### Step 1: Open Chrome Remote Desktop Website

1. Open Chrome browser on your Windows PC
2. Go to: **https://remotedesktop.google.com/access**
3. Sign in with your Google account

#### Step 2: Download and Install

1. Click **"Set up remote access"**
2. Click **"Download"** button
3. Run the installer when downloaded
4. Click **"Accept & Install"**

#### Step 3: Configure Access

1. Give your computer a name (e.g., "Neil-Desktop")
2. Set a **6-digit PIN** (you'll need this on iPad)
3. Click **"Start"**
4. Windows may ask for admin permission - click **Yes**

Your PC is now ready to receive connections.

#### Step 4: Verify It's Running

- Look for Chrome Remote Desktop icon in system tray (bottom right)
- Status should show as "Online"

---

### Part 2: iPad Setup

#### Step 1: Install the App

1. Open **App Store** on iPad
2. Search for **"Chrome Remote Desktop"**
3. Download the app by Google LLC (it's free)

#### Step 2: Sign In

1. Open the app
2. Sign in with the **same Google account** you used on PC

#### Step 3: Connect

1. You'll see your PC listed (e.g., "Neil-Desktop")
2. Tap on it
3. Enter your **6-digit PIN**
4. Your PC screen appears on iPad!

---

## How to Use It

### Touch Controls

| Action | How |
|--------|-----|
| Left click | Tap |
| Double click | Double tap |
| Right click | Tap with two fingers (or long press) |
| Scroll | Two finger swipe |
| Zoom | Pinch in/out |
| Pan around | Swipe (when zoomed in) |
| Show keyboard | Tap keyboard icon |

### Interface Buttons

The app has a toolbar (tap three-line menu icon):
- **Keyboard** - Show/hide on-screen keyboard
- **Trackpad mode** - Switch to cursor mode
- **Ctrl+Alt+Del** - Send to PC
- **Disconnect** - End session

### Split View Workflow (Claude + Remote Desktop)

1. Open Chrome Remote Desktop, connect to your PC
2. Swipe up from bottom to show dock
3. Drag Claude app icon to left or right side of screen
4. Now you have both apps side-by-side

**Workflow:**
```
Left side: Claude conversation
Right side: Your PC screen

Ask Claude for command → See command →
Tap right side → Run command → See result →
Tap left side → Discuss with Claude
```

---

## Optional Enhancements

### Connect Bluetooth Mouse

1. iPad Settings → Bluetooth → On
2. Put mouse in pairing mode
3. Tap mouse name when it appears
4. Mouse now works in remote desktop app (much easier!)

### Connect Bluetooth Keyboard

1. iPad Settings → Bluetooth → On
2. Put keyboard in pairing mode
3. Tap keyboard name when it appears
4. Full keyboard shortcuts now work

### Recommended Accessories

- **Logitech MX Keys Mini** - Compact, switches between devices
- **Logitech MX Anywhere 3** - Portable mouse, works on any surface
- **Apple Magic Keyboard** - Premium iPad integration
- Any generic Bluetooth mouse/keyboard works fine

---

## Troubleshooting

### PC Not Showing in iPad App

1. Check PC has internet connection
2. Verify Chrome Remote Desktop is running (check system tray)
3. Make sure you're signed into same Google account on both
4. Try refreshing the list in iPad app

### Connection Drops Frequently

1. Check WiFi signal strength on iPad
2. Check PC isn't going to sleep:
   - Windows Settings → System → Power → Screen/Sleep → Set to longer time
3. Keep Chrome browser open on PC (or use the standalone app)

### Laggy/Slow Performance

1. Reduce quality: In iPad app menu → Settings → Quality → Smooth
2. Connect iPad to 5GHz WiFi instead of 2.4GHz
3. Close unnecessary apps on both devices
4. If on mobile data, find better signal

### Can't Type Special Characters

1. Use the app's on-screen keyboard (tap keyboard icon)
2. Or connect a physical Bluetooth keyboard

---

## Security Notes

- Chrome Remote Desktop uses **TLS encryption** for all connections
- Your **6-digit PIN** is stored locally on the PC
- **Google account** authentication required
- Sessions don't stay open - you need to reconnect each time
- You can **remove PC access** anytime at remotedesktop.google.com

### Best Practices

1. Use a strong Google account password
2. Enable 2-factor authentication on Google account
3. Don't share your PIN with anyone
4. If iPad is lost, immediately revoke access from Google website

---

## Alternative: Tailscale + RDP (Advanced)

If you want more security and better performance, consider Tailscale + native Windows RDP.

### Why Choose This Instead?

| Criteria | Tailscale + RDP |
|----------|-----------------|
| Performance | Better (native Windows protocol) |
| Security | Better (private mesh VPN) |
| Setup | More complex (10-15 min) |
| Works offline? | Yes, on same network |

### Quick Setup Overview

1. Install Tailscale on Windows PC (tailscale.com)
2. Install Tailscale on iPad
3. Enable Remote Desktop on Windows (Settings → System → Remote Desktop → On)
4. Install Microsoft Remote Desktop app on iPad
5. Connect to your PC's Tailscale IP (100.x.x.x)

This creates a private encrypted network between your devices - more secure than going through Google's servers.

---

## Quick Reference Card

```
WINDOWS SETUP:
1. Chrome → remotedesktop.google.com/access
2. Download & install
3. Set name + 6-digit PIN

IPAD SETUP:
1. App Store → Chrome Remote Desktop
2. Sign in same Google account
3. Tap PC name → Enter PIN → Done!

CONTROLS:
Tap = Click
Double tap = Double click
Two-finger tap = Right click
Pinch = Zoom
```

---

## Summary

Chrome Remote Desktop is the easiest way to control your Windows PC from your iPad. Setup takes 3 minutes, it's free, secure, and reliable. Perfect for working with Claude on iPad while running commands on your PC.

Once set up, you can work from anywhere - couch, coffee shop, another room - while still having full access to your development environment.

---

*Document created: 2025-12-26*
*Location: CheckComputer/docs/IPAD-REMOTE-ACCESS-GUIDE.md*
