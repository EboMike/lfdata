"""Main application window for the LF data UI."""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lfdata.ui.canvas import LayoutCanvas
from lfdata.ui.config_manager import UIConfigManager
from lfdata.ui.preview import ImagePreview
from lfdata.ui.properties import PropertiesPanel


class LFDataUIApp(tk.Tk):
    """Main window class for the LF data UI application."""

    def __init__(self) -> None:
        """Initializes the main application window and components."""
        super().__init__()
        self.title('LF Data Video UI Configurator')
        self.geometry('1180x820')
        self.minsize(1024, 768)

        self.config_manager = UIConfigManager()

        self._create_menu()
        self._create_layout()

        # Load initial config to widgets
        self._sync_global_widgets()

    def _create_menu(self) -> None:
        """Creates the application menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=file_menu)
        file_menu.add_command(
            label='Open Configuration File', command=self._open_config
        )
        file_menu.add_command(
            label='Save Configuration File', command=self._save_config
        )
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.destroy)

    def _create_layout(self) -> None:
        """Sets up the grid layout divisions for the UI."""
        # Top-level horizontal paned window
        main_pane = ttk.PanedWindow(self, orient='horizontal')
        main_pane.pack(fill='both', expand=True, padx=5, pady=5)

        self._create_left_pane(main_pane)
        self._create_right_pane(main_pane)

        # Status Bar
        self.lbl_status = ttk.Label(
            self, text='Ready.', relief='sunken', anchor='w'
        )
        self.lbl_status.pack(fill='x', side='bottom', padx=5, pady=2)

    def _create_left_pane(self, parent: ttk.PanedWindow) -> None:
        """Creates the left vertical pane containing Canvas and Preview.

        Args:
            parent: The parent horizontal paned window.
        """
        left_vertical_pane = ttk.PanedWindow(
            parent, orient='vertical', width=680
        )
        parent.add(left_vertical_pane, weight=1)

        # Canvas Frame (Left - Top)
        canvas_container = ttk.LabelFrame(
            left_vertical_pane, text=' Screen Layout '
        )
        left_vertical_pane.add(canvas_container, weight=3)

        self.canvas = LayoutCanvas(
            canvas_container,
            self.config_manager,
            on_select_callback=self._on_element_selected,
        )
        self.canvas.pack(fill='both', expand=True, padx=5, pady=5)

        # Preview Frame (Left - Bottom)
        self.preview = ImagePreview(left_vertical_pane, self.config_manager)
        left_vertical_pane.add(self.preview, weight=2)

    def _create_right_pane(self, parent: ttk.PanedWindow) -> None:
        """Creates the right vertical pane containing Properties and Settings.

        Args:
            parent: The parent horizontal paned window.
        """
        right_vertical_pane = ttk.PanedWindow(
            parent, orient='vertical', width=380
        )
        parent.add(right_vertical_pane, weight=0)

        # Properties Frame (Right - Top)
        self.properties = PropertiesPanel(
            right_vertical_pane,
            self.config_manager,
            on_update_callback=self._on_properties_updated,
        )
        right_vertical_pane.add(self.properties, weight=3)

        # Global Settings Frame (Right - Bottom)
        settings_container = ttk.LabelFrame(
            right_vertical_pane, text=' Global Settings '
        )
        right_vertical_pane.add(settings_container, weight=2)
        self._create_global_settings(settings_container)

    def _create_global_settings(self, parent: ttk.LabelFrame) -> None:
        """Sets up buttons, inputs, listboxes, and tags inside global settings.

        Args:
            parent: The global settings parent container.
        """
        parent.grid_columnconfigure(1, weight=1)

        # Load TDF Button
        ttk.Label(parent, text='TDF Replay:').grid(
            row=0, column=0, sticky='w', padx=5, pady=5
        )
        self.btn_load_tdf = ttk.Button(
            parent, text='Load TDF File...', command=self._load_tdf
        )
        self.btn_load_tdf.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        # FPS Input
        ttk.Label(parent, text='Video FPS:').grid(
            row=1, column=0, sticky='w', padx=5, pady=5
        )
        self.fps_var = tk.StringVar()
        self.ent_fps = ttk.Entry(parent, textvariable=self.fps_var)
        self.ent_fps.grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        self.ent_fps.bind(
            '<FocusOut>', lambda e: self._on_global_setting_changed()
        )
        self.ent_fps.bind(
            '<Return>', lambda e: self._on_global_setting_changed()
        )

        # Video Size Inputs
        ttk.Label(parent, text='Video Width:').grid(
            row=2, column=0, sticky='w', padx=5, pady=5
        )
        self.width_var = tk.StringVar()
        self.ent_width = ttk.Entry(parent, textvariable=self.width_var)
        self.ent_width.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        self.ent_width.bind(
            '<FocusOut>', lambda e: self._on_global_setting_changed()
        )
        self.ent_width.bind(
            '<Return>', lambda e: self._on_global_setting_changed()
        )

        ttk.Label(parent, text='Video Height:').grid(
            row=3, column=0, sticky='w', padx=5, pady=5
        )
        self.height_var = tk.StringVar()
        self.ent_height = ttk.Entry(parent, textvariable=self.height_var)
        self.ent_height.grid(row=3, column=1, sticky='ew', padx=5, pady=5)
        self.ent_height.bind(
            '<FocusOut>', lambda e: self._on_global_setting_changed()
        )
        self.ent_height.bind(
            '<Return>', lambda e: self._on_global_setting_changed()
        )

        # Elements Listbox
        ttk.Label(parent, text='UI Elements:').grid(
            row=4, column=0, sticky='nw', padx=5, pady=5
        )
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=4, column=1, sticky='nsew', padx=5, pady=5)
        parent.rowconfigure(4, weight=1)

        self.lst_elements = tk.Listbox(
            list_frame,
            height=5,
            selectmode='single',
            bg='#1e1e1e',
            fg='#ffffff',
        )
        self.lst_elements.pack(side='left', fill='both', expand=True)
        self.lst_elements.bind('<<ListboxSelect>>', self._on_listbox_select)

        scrollbar = ttk.Scrollbar(
            list_frame, orient='vertical', command=self.lst_elements.yview
        )
        scrollbar.pack(side='right', fill='y')
        self.lst_elements.config(yscrollcommand=scrollbar.set)

        # Generate Video Button
        self.btn_gen_video = ttk.Button(
            parent, text='Generate Video...', command=self._generate_video
        )
        self.btn_gen_video.grid(
            row=5, column=0, columnspan=2, sticky='ew', padx=5, pady=10
        )

    def _sync_global_widgets(self) -> None:
        """Populates the global fields and listbox from the config manager."""
        cfg = self.config_manager.config
        self.fps_var.set(str(cfg.get('fps', 60)))

        res = cfg.get('resolution', [1920, 1080])
        self.width_var.set(str(res[0]))
        self.height_var.set(str(res[1]))

        # Populate elements listbox
        self.lst_elements.delete(0, 'end')
        elements = cfg.get('elements', {})
        for name in sorted(elements.keys()):
            self.lst_elements.insert('end', name)

    def _on_element_selected(self, name: str | None) -> None:
        """Handles selection sync when element is chosen via canvas or list.

        Args:
            name: The selected element name.
        """
        self.properties.load_element(name)

        # Synchronize listbox selection
        self.lst_elements.selection_clear(0, 'end')
        if name:
            try:
                idx = sorted(
                    self.config_manager.config.get('elements', {}).keys()
                ).index(name)
                self.lst_elements.selection_set(idx)
                self.lst_elements.see(idx)
            except ValueError:
                pass

    def _on_listbox_select(self, event: tk.Event) -> None:
        """Handles listbox item clicks to select element in canvas & forms.

        Args:
            event: The listbox selection event.
        """
        selection = self.lst_elements.curselection()
        if not selection:
            return
        idx = selection[0]
        name = self.lst_elements.get(idx)
        self.canvas.select_element(name)
        self.properties.load_element(name)

    def _on_properties_updated(self) -> None:
        """Updates layout preview when forms change."""
        self.canvas.refresh_elements()

    def _on_global_setting_changed(self) -> None:
        """Applies FPS and Resolution edits back to config."""
        try:
            fps = int(self.fps_var.get())
            self.config_manager.update_global_setting('fps', fps)
        except ValueError:
            pass

        try:
            w = int(self.width_var.get())
            h = int(self.height_var.get())
            self.config_manager.update_global_setting('resolution', [w, h])
        except ValueError:
            pass

    def _load_tdf(self) -> None:
        """Prompts user to select a TDF file and parses it."""
        path = filedialog.askopenfilename(
            title='Open TDF Replay File',
            filetypes=[('TDF Files', '*.tdf'), ('All Files', '*.*')],
        )
        if not path:
            return

        self.lbl_status.config(text=f'Loading TDF: {os.path.basename(path)}...')
        self.update_idletasks()

        try:
            self.config_manager.load_tdf(path)
            self.preview.on_tdf_loaded()
            self.lbl_status.config(text=f'TDF Loaded: {os.path.basename(path)}')
        except Exception as e:
            messagebox.showerror('Error Loading TDF', str(e))
            self.lbl_status.config(text='Failed to load TDF.')

    def _open_config(self) -> None:
        """Prompts user to load a YAML config file and updates UI elements."""
        path = filedialog.askopenfilename(
            title='Open Configuration File',
            filetypes=[('YAML Files', '*.yaml'), ('All Files', '*.*')],
        )
        if not path:
            return

        try:
            self.config_manager.load_config(path)
            self._sync_global_widgets()
            self.canvas.select_element(None)
            self.canvas.refresh_elements()
            self.preview.update_preview()
            self.lbl_status.config(
                text=f'Loaded config: {os.path.basename(path)}'
            )
        except Exception as e:
            messagebox.showerror('Error Loading Config', str(e))

    def _save_config(self) -> None:
        """Prompts user to save current config to a YAML file."""
        path = filedialog.asksaveasfilename(
            title='Save Configuration File',
            defaultextension='.yaml',
            filetypes=[('YAML Files', '*.yaml'), ('All Files', '*.*')],
        )
        if not path:
            return

        try:
            self.config_manager.save_config(path)
            self.lbl_status.config(
                text=f'Saved config: {os.path.basename(path)}'
            )
        except Exception as e:
            messagebox.showerror('Error Saving Config', str(e))

    def _generate_video(self) -> None:
        """Triggers the video generation flow with path selection and background thread."""
        if not self.config_manager.tdf_path:
            messagebox.showwarning(
                'Missing TDF', 'Please load a TDF replay file first.'
            )
            return

        out_path = filedialog.asksaveasfilename(
            title='Save Generated Video',
            filetypes=[
                ('WebM Video', '*.webm'),
                ('QuickTime Movie', '*.mov'),
                ('MP4 Video', '*.mp4'),
                ('All Files', '*.*'),
            ],
        )
        if not out_path:
            return

        # Save config to a temporary file for rendering
        import tempfile

        temp_cfg = os.path.join(tempfile.gettempdir(), 'video_gen_config.yaml')
        self.config_manager.save_config(temp_cfg)

        player_focus = self.preview.player_var.get()
        player_focus_param = (
            player_focus if player_focus and player_focus != 'None' else None
        )

        # Disable compile button and start thread
        self.btn_gen_video['state'] = tk.DISABLED
        self.lbl_status.config(text='Generating video, please wait...')

        threading.Thread(
            target=self._run_video_compilation,
            args=(out_path, temp_cfg, player_focus_param),
            daemon=True,
        ).start()

    def _run_video_compilation(
        self, output_path: str, temp_cfg_path: str, player_focus: str | None
    ) -> None:
        """Background thread worker to compile the video via lfdata subprocess.

        Args:
            output_path: The target video output path.
            temp_cfg_path: The temporary config YAML file path.
            player_focus: The player focus name.
        """
        cmd = self.config_manager.get_lfdata_command() + [
            '--input_tdf',
            self.config_manager.tdf_path,
            '--config',
            temp_cfg_path,
            '--video_out',
            output_path,
        ]
        if player_focus:
            cmd.extend(['--video_player', player_focus])

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Safe callback to main GUI thread
            self.after(
                0,
                self._on_compilation_done,
                True,
                f'Video generated successfully at: {output_path}',
            )
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr or e.stdout or str(e)
            self.after(
                0,
                self._on_compilation_done,
                False,
                f'Compilation failed:\n{err_msg}',
            )
        except Exception as e:
            self.after(
                0, self._on_compilation_done, False, f'Unexpected error: {e}'
            )

    def _on_compilation_done(self, success: bool, msg: str) -> None:
        """Called on the main thread when compilation finishes.

        Args:
            success: Whether compilation was successful.
            msg: The completion or error message.
        """
        self.btn_gen_video['state'] = tk.NORMAL
        if success:
            self.lbl_status.config(text='Video generation completed.')
            messagebox.showinfo('Success', msg)
        else:
            self.lbl_status.config(text='Video generation failed.')
            messagebox.showerror('Generation Error', msg)
