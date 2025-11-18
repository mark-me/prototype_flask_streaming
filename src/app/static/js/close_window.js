function close_window(warning = False) {
    if (warning) {
        if (confirm("Wil je deze tab afsluiten?\nWijzigingen worden niet opgeslagen.")) {
            close();
        }
    } else {
        close();
    }
}
