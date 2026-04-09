# MITM Proxy Guide — ZeroMOUSE iOS App Capture

## What this does

You run a proxy on your Mac. Your iPhone sends all its traffic through it.
You can see (and save) every HTTP/HTTPS request the ZeroMOUSE app makes,
including the AWS Cognito tokens we need for Phase 3.

---

## Step 1: Install mitmproxy

```bash
brew install mitmproxy
```

Verify:
```bash
mitmweb --version
```

---

## Step 2: Start mitmweb

From the zeromouse project directory:

```bash
cd ~/Developer/zeromouse
mitmweb -s mitmproxy-capture.py
```

This starts:
- **Proxy** on port `8080` (your iPhone will connect here)
- **Web UI** on `http://127.0.0.1:8081` (opens in your browser automatically — this is where you see all traffic live)

The capture script auto-saves interesting AWS/Cognito traffic to `zeromouse-captures.json`.

---

## Step 3: Find your Mac's IP

Your Mac's current IP (on Wi-Fi):

```bash
ifconfig en0 | grep "inet "
```

Note the IP (e.g. `10.10.10.137`). Your iPhone needs this.

---

## Step 4: Configure iPhone to use the proxy

Both devices must be on the **same Wi-Fi network**.

1. On iPhone: **Settings → Wi-Fi**
2. Tap the **(i)** next to your connected network
3. Scroll down to **HTTP Proxy** → tap **Configure Proxy**
4. Select **Manual**
5. Enter:
   - **Server:** `10.10.10.137` (your Mac's IP from Step 3)
   - **Port:** `8080`
6. Tap **Save**

At this point, HTTP traffic flows through mitmproxy. But HTTPS won't work yet — you need to install the mitmproxy CA certificate.

---

## Step 5: Install the mitmproxy CA certificate on iPhone

1. **With the proxy still active**, open Safari on your iPhone
2. Go to: **http://mitm.it**
3. Tap **Apple** (the iOS icon)
4. It will prompt to download a profile — tap **Allow**
5. Go to: **Settings → General → VPN & Device Management**
6. You'll see **mitmproxy** under "Downloaded Profile" — tap it
7. Tap **Install** → enter your passcode → tap **Install** again
8. Now go to: **Settings → General → About → Certificate Trust Settings**
9. Toggle **ON** for "mitmproxy" under "Enable Full Trust for Root Certificates"
10. Confirm the warning

HTTPS interception is now active.

---

## Step 6: Capture ZeroMOUSE traffic

1. Check the mitmweb UI at `http://127.0.0.1:8081` — you should already see traffic flowing (Safari requests, iCloud, etc.)
2. Open the **ZeroMOUSE app** on your iPhone
3. Do these actions in the app:
   - Open the app (triggers Cognito login)
   - View the device status
   - Trigger a detection event if possible (walk past the sensor)
   - Toggle the flap lock on/off
   - View event history / images
4. Watch the mitmweb UI — look for requests to:
   - `cognito-idp.eu-central-1.amazonaws.com` (user pool auth)
   - `cognito-identity.eu-central-1.amazonaws.com` (identity pool)
   - `*.iot.eu-central-1.amazonaws.com` (IoT endpoints)
   - `execute-api` domains (REST API)
5. The capture script highlights these with `[ZM] ***` in the event log

---

## Step 7: Review captures

The script saves all AWS-related traffic to:

```bash
cat ~/Developer/zeromouse/zeromouse-captures.json | python3 -m json.tool
```

What we're looking for:

| Capture | Why we need it |
|---------|---------------|
| Cognito User Pool ID | `eu-central-1_XXXXXXX` — identifies the auth pool |
| Cognito Identity Pool ID | `eu-central-1:xxxxxxxx-xxxx-...` — for getting AWS creds |
| App Client ID | Used in the Cognito `InitiateAuth` call |
| IdToken / AccessToken | JWT tokens from Cognito sign-in |
| IdentityId | The Cognito identity linked to your account |
| AWS temp credentials | `AccessKeyId`, `SecretKey`, `SessionToken` from `GetCredentialsForIdentity` |
| IoT endpoint URL | Should match `a1lrk6d93bvma9-ats.iot.eu-central-1.amazonaws.com` |
| MQTT WebSocket URL | If the app uses WS for real-time updates |

---

## Step 8: Clean up when done

On your iPhone:
1. **Settings → Wi-Fi → (i) → HTTP Proxy → Off**
2. Optionally remove the cert: **Settings → General → VPN & Device Management → mitmproxy → Remove Profile**

---

## Troubleshooting

### "App won't connect" / SSL errors
Some apps use **certificate pinning** — they reject any cert that isn't the expected one. If the ZeroMOUSE app refuses to load data:

- Check if the app shows its own error or just blank/loading
- The mitmweb UI will show red `CONNECT` entries that fail (TLS handshake errors)
- If pinned: we can try `ssl_insecure` mode, or use Frida to bypass pinning (more advanced — ask me)

### No traffic showing up
- Confirm both devices are on the same Wi-Fi
- Confirm proxy settings on iPhone (server IP + port 8080)
- Test by opening any website in Safari — you should see it in mitmweb

### mitm.it won't load
- The proxy must be running and iPhone must be using it
- Use Safari, not Chrome (Chrome may not offer to install the profile)
