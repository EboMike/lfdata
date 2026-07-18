"""Startup verification and environment checking for the LF data tool."""

from pathlib import Path


class StartupVerifier:
    """Verifier for startup requirements of the LF data tool."""

    @classmethod
    def check_assets_and_print_cwd(cls) -> None:
        """Prints the current directory and checks if all required assets exist.

        This function is run on application startup to ensure that vital visual
        and font asset files are present in the expected paths relative to the
        current working directory.

        Raises:
            FileNotFoundError: If any of the required asset files is missing.
        """
        cwd = Path.cwd()
        print(f'Current directory: {cwd}')

        required_paths = [
            # Fonts
            Path('fonts/Anton-Regular.ttf'),
            Path('fonts/D Day Stencil.ttf'),
            Path('fonts/DMSans-Bold.ttf'),
            Path('fonts/DMSans-ExtraBold.ttf'),
            Path('fonts/GoogleSans-Bold.ttf'),
            Path('fonts/GoogleSans-VariableFont_GRAD,opsz,wght.ttf'),
            Path('fonts/Nasalization Rg.otf'),
            Path('fonts/Poppins-Regular.ttf'),
            Path('fonts/advanced_pixel_lcd-7.ttf'),
            # Main assets
            Path('assets/discord.png'),
            Path('assets/downtime-empty.png'),
            Path('assets/downtime-full.png'),
            Path('assets/hit_border.png'),
            Path('assets/lives.png'),
            Path('assets/missiles.png'),
            Path('assets/penalty.png'),
            Path('assets/shield_empty.png'),
            Path('assets/shield_full.png'),
            Path('assets/shields.png'),
            Path('assets/shots.png'),
            Path('assets/sp.png'),
            # SM5 role icons
            Path('assets/sm5/ammo.png'),
            Path('assets/sm5/commander.png'),
            Path('assets/sm5/heavy.png'),
            Path('assets/sm5/medic.png'),
            Path('assets/sm5/scout.png'),
        ]

        for rel_path in required_paths:
            if not rel_path.exists():
                raise FileNotFoundError(f'Required asset not found: {rel_path}')
