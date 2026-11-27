#!/usr/bin/env bash
# systemd unitlarini o'rnatish (sudo bilan): sudo deploy/install.sh
# Tartib: postgresql, redis → fcv-migrate → api; video → inference → trainer; api → telegram.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="${SUDO_USER:-$(id -un)}"
[[ $EUID -eq 0 ]] || { echo "sudo bilan ishga tushiring"; exit 1; }
for f in "$ROOT"/deploy/systemd/*; do
  sed -e "s|@ROOT@|$ROOT|g" -e "s|@USER@|$USER_NAME|g" "$f" > "/etc/systemd/system/$(basename "$f")"
done
systemctl daemon-reload
systemctl enable fcv.target fcv-api fcv-video fcv-logic fcv-inference fcv-trainer fcv-telegram fcv-backup.timer

# UI orqali avtomatik ishga tushishni boshqarish (Umumiy sozlamalar → Avtomatik ishga tushish):
# root yordamchi skript + faqat shu skript uchun parolsiz sudo (Ubuntu 26.04: sudo-rs, /etc/sudoers.d)
HELPER=/usr/local/sbin/fcv-autostart
sed -e "s|@USER@|$USER_NAME|g" "$ROOT/deploy/fcv-autostart" > "$HELPER.tmp"
chown root:root "$HELPER.tmp"; chmod 755 "$HELPER.tmp"; mv "$HELPER.tmp" "$HELPER"
SUDOERS=/etc/sudoers.d/fcv-autostart
echo "$USER_NAME ALL=(root) NOPASSWD: $HELPER" > "$SUDOERS.tmp"
chmod 440 "$SUDOERS.tmp"
if command -v visudo >/dev/null && ! visudo -cf "$SUDOERS.tmp" >/dev/null; then
  rm -f "$SUDOERS.tmp"; echo "sudoers qoidasi xato — UI dan avtomatik ishga tushishni boshqarib bo'lmaydi" >&2
else
  mv "$SUDOERS.tmp" "$SUDOERS"
fi
echo "O'rnatildi. Ishga tushirish: sudo systemctl start fcv.target"
