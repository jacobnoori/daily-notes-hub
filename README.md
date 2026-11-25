# daily-notes-hub

Pre-creates Obsidian daily notes (today + 7 days) on the Syncthing hub, so devices
never create them independently and conflict.

## Install on the hub

Needs `git` and `python3` (`apt install -y git python3-minimal`).

    git clone https://github.com/jacobnoori/daily-notes-hub.git /opt/daily-notes-hub

    # Machine-specific config (kept out of the repo). Find the path with
    # `syncthing cli config folders list` / `syncthing cli config folders <id> path get`.
    echo 'VAULT=/path/to/Obsidian Vault' > /etc/default/daily-notes

    # Test without writing anything:
    python3 -I /opt/daily-notes-hub/precreate-daily-notes.py "/path/to/Obsidian Vault" --dry-run

    systemctl link /opt/daily-notes-hub/daily-notes.service /opt/daily-notes-hub/daily-notes.timer
    systemctl enable --now daily-notes.timer
    systemctl start daily-notes.service && journalctl -u daily-notes.service -n 20

No quotes are needed around a VAULT value with spaces in `/etc/default/daily-notes`.

## Update

    cd /opt/daily-notes-hub && git pull && systemctl daemon-reload

## Behavior

- Never overwrites: files are created with O_EXCL and existing notes are skipped.
- Refuses to run if the vault path has no `.stfolder` (e.g. unmounted disk).
- Renders `Templates/Daily note.md` itself: `tp.file.title`, `tp.file.cursor()`,
  and the Quotes exec block. If you add any other Templater tag to the template, the
  script exits with an error (check `journalctl -u daily-notes`) and writes nothing
  until `render_tag()` is updated.
- Templater on devices ignores these notes (it only templates empty new files), and its
  folder template stays as a fallback for dates the hub didn't create.
