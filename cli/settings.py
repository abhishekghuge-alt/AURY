from pathlib import Path
from core import config, database
from cli import ui

def run_settings() -> None:
    while True:
        # Load current settings from DB
        df = database.db.get_setting("download_dir", str(config.DOWNLOAD_DIR))
        dq = database.db.get_setting("default_quality", str(config.DEFAULT_QUALITY_KEY))
        mw = database.db.get_setting("max_workers", str(config.MAX_WORKERS))
        turbo = database.db.get_setting("aria2c_turbo", "auto")
        sub_def = database.db.get_setting("default_subtitles", "false")
        sub_lang = database.db.get_setting("default_sub_lang", "en")

        choice = ui.show_settings_menu(df, dq, mw, turbo, sub_def, sub_lang)

        if choice == "1":
            new_folder = ui.prompt_new_folder(df)
            if new_folder:
                Path(new_folder).mkdir(parents=True, exist_ok=True)
                database.db.set_setting("download_dir", new_folder)
                database.db.sync_config_with_db()
                
        elif choice == "2":
            res = ui.prompt_quality("default quality", return_index=True)
            if res:
                idx = res[0]
                database.db.set_setting("default_quality", idx)
                database.db.sync_config_with_db()
                
        elif choice == "3":
            new_mw = ui.prompt_max_workers(mw)
            database.db.set_setting("max_workers", new_mw)
            database.db.sync_config_with_db()
            
        elif choice == "4":
            new_turbo = "off" if turbo == "auto" else "auto"
            database.db.set_setting("aria2c_turbo", new_turbo)
            
        elif choice == "5":
            new_sub_def = "false" if sub_def.lower() == "true" else "true"
            database.db.set_setting("default_subtitles", new_sub_def)
            
        elif choice == "6":
            new_sub_lang = ui.prompt_sub_lang(sub_lang)
            if new_sub_lang:
                database.db.set_setting("default_sub_lang", new_sub_lang)
                
        elif choice == "7":
            if ui.prompt_clear_history_confirm():
                count = database.db.clear_all_history()
                ui.console.print(f"[success]✔ History cleared. {count} records deleted.[/]")
                
        elif choice == "8":
            stats = database.db.get_advanced_stats()
            ui.show_advanced_stats(stats)
            
        elif choice == "9":
            break
