A cheat sheet for managing a GitHub account from inside a remote server
(e.g., an SSH session opened through a terminal app).

------

## 1. First-Time Setup

### Set your Git identity (on the server)

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Use the same email that's on your GitHub account.

### Generate an SSH key (on the server)

```bash
ssh-keygen -t ed25519 -C "you@example.com"
```

Press Enter to accept the default path (`~/.ssh/id_ed25519`).
Set a passphrase or leave it blank.

### Show the public key and copy it

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire line. This is the **public** half.
Never copy the file *without* the `.pub` — that one stays secret.

### Add the key to GitHub

In your browser:
**GitHub → Settings → SSH and GPG keys → New SSH key**
Paste the key, give it a name, and save.

### Test the connection

```bash
ssh -T git@github.com
```

Success looks like: `Hi username! You've successfully authenticated...`
(It won't give you a shell — that's normal.)

---

## 2. Troubleshooting the Connection Test

### "Permission denied (publickey)"

The server offered a key GitHub didn't recognize. Check the following.

```bash
# Is a key loaded into the agent?
ssh-add -l

# If the agent isn't running, start it and add your key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Confirm the key files actually exist
ls -la ~/.ssh/
```

Also re-check that the public key was pasted into GitHub with no broken
line breaks or stray spaces.

### "Bad permissions" / "UNPROTECTED PRIVATE KEY FILE"

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### "Connection timed out" / "Connection refused"

The server can't reach GitHub on port 22 (often a firewall). Try routing
Git over port 443 instead:

```bash
ssh -T -p 443 git@ssh.github.com
```

### "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!"

Usually harmless. It means the server has an outdated copy of GitHub's host
key saved. Remove the stale entry and reconnect:

```bash
ssh-keygen -R github.com
ssh -T git@github.com
```

When prompted, only type `yes` if the shown fingerprint matches one of
GitHub's official published fingerprints:

| Key type | Fingerprint |
|----------|-------------|
| RSA      | `SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s` |
| ECDSA    | `SHA256:p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM` |
| Ed25519  | `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU` |

Never type `yes` blindly — always match the fingerprint first.

---

## 3. Downloading a Repository (Clone)

```bash
git clone git@github.com:username/repo.git
cd repo
```

The clone URL must use the `git@github.com:` (SSH) form, not `https://`.
Everything below happens *inside* the repo folder.

---

## 4. Adding Files and Pushing Them Up

The core loop — same order every time.

```bash
# 1. Create or edit a file (example)
echo "hello world" > notes.txt

# 2. Stage the change ("put it in the box")
git add notes.txt
# ...or stage everything you changed:
git add .

# 3. Commit locally ("seal and label the box")
git commit -m "Add notes file"

# 4. Push to GitHub ("hand it to the courier")
git push
```

Nothing reaches GitHub until the `push`. Commits alone stay local.

**First push on a brand-new repo** may need:

```bash
git push -u origin main
```

The `-u` links your local branch to GitHub so later pushes are just
`git push`. Git will tell you if this is needed.

---

## 5. Pulling Down Changes

Grab the latest before you start working each session:

```bash
git pull
```

---

## 6. Checking Status

Run this anytime you're unsure what's going on:

```bash
git status
```

It shows what's staged, what's changed, and what's safe to push.

---

## 7. Listing Repositories (needs the `gh` CLI)

Plain `git` and SSH **cannot list your repos**. Use GitHub's own CLI tool,
`gh`.

### Check if it's installed

```bash
gh --version
```

### Install it (Ubuntu / Debian)

```bash
sudo apt update && sudo apt install gh
```

### Log in once

```bash
gh auth login
```

Choose **GitHub.com**, then **SSH** as the protocol (already set up above).

### List your repos

```bash
gh repo list

# show more at once
gh repo list --limit 100
```

### Bonus — clone by name alone

```bash
gh repo clone username/repo
```

---

## Command Summary

| Task | Command |
|------|---------|
| Set name/email | `git config --global user.name/user.email ...` |
| Make SSH key | `ssh-keygen -t ed25519 -C "email"` |
| Show public key | `cat ~/.ssh/id_ed25519.pub` |
| Test GitHub auth | `ssh -T git@github.com` |
| Fix changed host key | `ssh-keygen -R github.com` |
| Clone a repo | `git clone git@github.com:user/repo.git` |
| Stage changes | `git add .` |
| Commit | `git commit -m "message"` |
| Upload | `git push` |
| Download updates | `git pull` |
| Check state | `git status` |
| List repos | `gh repo list` |
