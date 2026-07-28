using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("ScriptHub Campus 桌宠播放器")]
[assembly: AssemblyDescription("导入并运行 ScriptHub Campus 生成的 .petpack 桌宠资源包")]
[assembly: AssemblyCompany("Berry Studio")]
[assembly: AssemblyProduct("桌宠播放器")]
[assembly: AssemblyVersion("1.1.0.0")]
[assembly: AssemblyFileVersion("1.1.0.0")]

namespace DesktopPetPlayer
{
    internal static class Program
    {
#if !SELF_TEST
        private static Mutex _singleInstance;
#endif

        [STAThread]
        public static void Main(string[] arguments)
        {
#if SELF_TEST
            Environment.Exit(PlayerSelfTest.Run(arguments));
#else
            bool isFirstInstance;
#if VISUAL_TEST
            string mutexName = "Local\\DesktopPetPlayer_v1_VisualTest";
#else
            string mutexName = "Local\\DesktopPetPlayer_v1";
#endif
            _singleInstance = new Mutex(true, mutexName, out isFirstInstance);
            if (!isFirstInstance)
            {
                MessageBox.Show("桌宠播放器已经在运行，请使用托盘菜单导入新的桌宠包。",
                    "桌宠播放器", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            try
            {
                string requestedPack = arguments.Length > 0 ? arguments[0] : null;
                Application.Run(new PetPlayerForm(requestedPack));
            }
            catch (Exception exception)
            {
                MessageBox.Show("桌宠播放器遇到问题，请重新打开。\n\n" + exception.Message,
                    "桌宠播放器", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                _singleInstance.ReleaseMutex();
                _singleInstance.Dispose();
            }
#endif
        }
    }

#if SELF_TEST
    internal static class PlayerSelfTest
    {
        public static int Run(string[] arguments)
        {
            if (arguments.Length != 1 || !File.Exists(arguments[0]))
                return 2;
            try
            {
                using (PetPackage package = PetPackage.Load(arguments[0]))
                {
                    if (String.IsNullOrWhiteSpace(package.Name) ||
                        package.Actions == null ||
                        package.Actions.Count < 1)
                        return 3;
                }
                using (PackageImportForm dialog = new PackageImportForm(null))
                {
                    if (dialog.Text != "导入桌宠包" ||
                        !dialog.ShowInTaskbar ||
                        !dialog.AllowDrop)
                        return 4;
                }
                return 0;
            }
            catch (Exception)
            {
                return 1;
            }
        }
    }
#endif

    internal sealed class PackageImportForm : Form
    {
        private readonly Label _dropLabel;

        public string SelectedPath { get; private set; }

        public PackageImportForm(string currentPackage)
        {
            Text = "导入桌宠包";
            ClientSize = new Size(560, 360);
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            ShowInTaskbar = true;
            TopMost = true;
            BackColor = Color.White;
            Font = new Font("Microsoft YaHei UI", 9F, FontStyle.Regular);
            AllowDrop = true;

            Label title = new Label();
            title.AutoSize = false;
            title.Location = new Point(28, 24);
            title.Size = new Size(504, 36);
            title.Font = new Font(Font.FontFamily, 17F, FontStyle.Bold);
            title.Text = "导入你制作的桌宠";
            Controls.Add(title);

            Label description = new Label();
            description.AutoSize = false;
            description.Location = new Point(30, 67);
            description.Size = new Size(500, 46);
            description.ForeColor = Color.FromArgb(71, 85, 105);
            description.Text = "选择网站生成的 .petpack 文件。也可以把资源包直接拖到下方区域。";
            Controls.Add(description);

            Panel dropArea = new Panel();
            dropArea.Location = new Point(30, 120);
            dropArea.Size = new Size(500, 118);
            dropArea.BorderStyle = BorderStyle.FixedSingle;
            dropArea.BackColor = Color.FromArgb(239, 246, 255);
            dropArea.AllowDrop = true;
            Controls.Add(dropArea);

            _dropLabel = new Label();
            _dropLabel.Dock = DockStyle.Fill;
            _dropLabel.TextAlign = ContentAlignment.MiddleCenter;
            _dropLabel.Font = new Font(Font.FontFamily, 11F, FontStyle.Bold);
            _dropLabel.ForeColor = Color.FromArgb(29, 78, 216);
            _dropLabel.Text = "把 .petpack 拖到这里\n或点击“选择桌宠包”";
            _dropLabel.AllowDrop = true;
            dropArea.Controls.Add(_dropLabel);

            Label current = new Label();
            current.AutoSize = false;
            current.Location = new Point(30, 250);
            current.Size = new Size(500, 32);
            current.ForeColor = Color.FromArgb(100, 116, 139);
            current.Text = String.IsNullOrWhiteSpace(currentPackage)
                ? "当前还没有导入桌宠包"
                : "当前桌宠：" + Path.GetFileName(currentPackage);
            Controls.Add(current);

            Button chooseButton = new Button();
            chooseButton.Location = new Point(300, 300);
            chooseButton.Size = new Size(136, 38);
            chooseButton.Text = "选择桌宠包";
            chooseButton.UseVisualStyleBackColor = true;
            chooseButton.Click += delegate { ChoosePackage(); };
            Controls.Add(chooseButton);

            Button cancelButton = new Button();
            cancelButton.Location = new Point(446, 300);
            cancelButton.Size = new Size(84, 38);
            cancelButton.Text = "取消";
            cancelButton.DialogResult = DialogResult.Cancel;
            cancelButton.UseVisualStyleBackColor = true;
            Controls.Add(cancelButton);

            AcceptButton = chooseButton;
            CancelButton = cancelButton;

            DragEnter += OnPackageDragEnter;
            DragDrop += OnPackageDragDrop;
            dropArea.DragEnter += OnPackageDragEnter;
            dropArea.DragDrop += OnPackageDragDrop;
            _dropLabel.DragEnter += OnPackageDragEnter;
            _dropLabel.DragDrop += OnPackageDragDrop;
        }

        private void ChoosePackage()
        {
            using (OpenFileDialog dialog = new OpenFileDialog())
            {
                dialog.Title = "选择网站生成的桌宠资源包";
                dialog.Filter = "桌宠资源包 (*.petpack;*.zip)|*.petpack;*.zip|所有文件 (*.*)|*.*";
                dialog.CheckFileExists = true;
                dialog.Multiselect = false;
                dialog.RestoreDirectory = true;

                string downloads = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "Downloads");
                if (Directory.Exists(downloads))
                    dialog.InitialDirectory = downloads;

                if (dialog.ShowDialog(this) == DialogResult.OK)
                    AcceptPackage(dialog.FileName);
            }
        }

        private void OnPackageDragEnter(object sender, DragEventArgs e)
        {
            e.Effect = GetDroppedPackage(e.Data) == null
                ? DragDropEffects.None
                : DragDropEffects.Copy;
        }

        private void OnPackageDragDrop(object sender, DragEventArgs e)
        {
            string path = GetDroppedPackage(e.Data);
            if (path != null)
                AcceptPackage(path);
        }

        private static string GetDroppedPackage(IDataObject data)
        {
            if (data == null || !data.GetDataPresent(DataFormats.FileDrop))
                return null;
            string[] files = data.GetData(DataFormats.FileDrop) as string[];
            if (files == null || files.Length != 1 || !File.Exists(files[0]))
                return null;
            string extension = Path.GetExtension(files[0]);
            if (!String.Equals(extension, ".petpack", StringComparison.OrdinalIgnoreCase) &&
                !String.Equals(extension, ".zip", StringComparison.OrdinalIgnoreCase))
                return null;
            return files[0];
        }

        private void AcceptPackage(string path)
        {
            SelectedPath = Path.GetFullPath(path);
            DialogResult = DialogResult.OK;
            Close();
        }
    }

    internal sealed class PetPlayerForm : Form
    {
        private const string CurrentPlayerVersion = "1.1.0";
        private const int WsExLayered = 0x00080000;
        private const int WmNcHitTest = 0x0084;
        private const int HtClient = 1;
        private const int HtTransparent = -1;
        // A tiny movement cancels a click, while a larger movement actually
        // starts moving the window. Keeping these thresholds separate prevents
        // a short drag from being mistaken for a click.
        private const int ClickMovementTolerance = 3;
        private const int DragActivationDistance = 12;
        private const int UlwAlpha = 0x00000002;
        private const byte AcSrcOver = 0x00;
        private const byte AcSrcAlpha = 0x01;

        private readonly PlayerSettings _settings;
        private readonly string _requestedPack;
        private readonly System.Windows.Forms.Timer _animationTimer;
        private readonly Random _random;
        private readonly ToolStripMenuItem _actionsMenu;
        private readonly ToolStripMenuItem _topmostItem;
        private readonly List<ToolStripMenuItem> _sizeItems;
        private readonly NotifyIcon _trayIcon;

        private PetPackage _package;
        private int _currentActionIndex;
        private int _petSize;
        private byte[] _hitMask;
        private bool _pointerDown;
        private bool _pointerMoved;
        private bool _dragging;
        private Point _pointerDownScreen;
        private Point _windowDownLocation;

        public PetPlayerForm(string requestedPack)
        {
            _settings = PlayerSettings.Load();
            _requestedPack = requestedPack;
            _random = new Random();
            _petSize = _settings.HasSize && _settings.Size >= 72 && _settings.Size <= 320 ? _settings.Size : 120;

            Text = "桌宠播放器";
            ClientSize = new Size(_petSize, _petSize);
            MinimumSize = new Size(72, 72);
            FormBorderStyle = FormBorderStyle.None;
            StartPosition = FormStartPosition.Manual;
            TopMost = _settings.TopMost;
            MaximizeBox = false;
            MinimizeBox = false;
            Cursor = Cursors.Hand;
            AllowDrop = true;
#if VISUAL_TEST
            ShowInTaskbar = true;
#else
            ShowInTaskbar = false;
#endif

            _animationTimer = new System.Windows.Forms.Timer();
            _animationTimer.Tick += OnAnimationTick;

            ContextMenuStrip menu = new ContextMenuStrip();
            menu.ShowImageMargin = false;

            _actionsMenu = new ToolStripMenuItem("动作");
            menu.Items.Add(_actionsMenu);

            ToolStripMenuItem importItem = new ToolStripMenuItem("导入 / 更换桌宠包…");
            importItem.Click += delegate { ImportPackage(); };
            menu.Items.Add(importItem);
            menu.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem sizeMenu = new ToolStripMenuItem("大小");
            _sizeItems = new List<ToolStripMenuItem>();
            AddSizeItem(sizeMenu, "迷你（90px）", 90);
            AddSizeItem(sizeMenu, "小巧（120px）", 120);
            AddSizeItem(sizeMenu, "稍大（160px）", 160);
            menu.Items.Add(sizeMenu);

            _topmostItem = new ToolStripMenuItem("始终置顶");
            _topmostItem.CheckOnClick = true;
            _topmostItem.Checked = TopMost;
            _topmostItem.CheckedChanged += delegate
            {
                TopMost = _topmostItem.Checked;
                _settings.TopMost = TopMost;
            };
            menu.Items.Add(_topmostItem);

            ToolStripMenuItem resetItem = new ToolStripMenuItem("回到右下角");
            resetItem.Click += delegate { MoveToBottomRight(); };
            menu.Items.Add(resetItem);

            menu.Items.Add(new ToolStripSeparator());
            ToolStripMenuItem exitItem = new ToolStripMenuItem("退出播放器");
            exitItem.Click += delegate { Close(); };
            menu.Items.Add(exitItem);
            ContextMenuStrip = menu;

            ContextMenuStrip trayMenu = new ContextMenuStrip();
            ToolStripMenuItem trayImport = new ToolStripMenuItem("导入 / 更换桌宠包…");
            trayImport.Click += delegate { ImportPackage(); };
            trayMenu.Items.Add(trayImport);
            ToolStripMenuItem trayReset = new ToolStripMenuItem("回到右下角");
            trayReset.Click += delegate { MoveToBottomRight(); };
            trayMenu.Items.Add(trayReset);
            trayMenu.Items.Add(new ToolStripSeparator());
            ToolStripMenuItem trayExit = new ToolStripMenuItem("退出播放器");
            trayExit.Click += delegate { Close(); };
            trayMenu.Items.Add(trayExit);

            Icon trayImage = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            _trayIcon = new NotifyIcon();
            _trayIcon.Icon = trayImage ?? SystemIcons.Application;
            _trayIcon.Text = "桌宠播放器";
            _trayIcon.ContextMenuStrip = trayMenu;
            _trayIcon.Visible = true;
            _trayIcon.DoubleClick += delegate
            {
                BeginInvoke(new Action(ImportPackage));
            };

            MouseDown += OnPointerDown;
            MouseMove += OnPointerMove;
            MouseUp += OnPointerUp;
            DragEnter += OnPackageDragEnter;
            DragDrop += OnPackageDragDrop;
            Shown += OnShown;
            FormClosing += OnFormClosing;
        }

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams parameters = base.CreateParams;
                parameters.ExStyle |= WsExLayered;
                return parameters;
            }
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
        }

        protected override void OnPaint(PaintEventArgs e)
        {
        }

        protected override void WndProc(ref Message message)
        {
            base.WndProc(ref message);
            if (message.Msg != WmNcHitTest)
                return;

            long packed = message.LParam.ToInt64();
            int screenX = (short)(packed & 0xffff);
            int screenY = (short)((packed >> 16) & 0xffff);
            Point client = PointToClient(new Point(screenX, screenY));
            if (client.X < 0 || client.Y < 0 || client.X >= _petSize || client.Y >= _petSize)
            {
                message.Result = new IntPtr(HtTransparent);
                return;
            }

            int maskIndex = (client.Y * _petSize) + client.X;
            if (_hitMask == null || maskIndex < 0 || maskIndex >= _hitMask.Length || _hitMask[maskIndex] < 16)
                message.Result = new IntPtr(HtTransparent);
            else
                message.Result = new IntPtr(HtClient);
        }

        private void OnShown(object sender, EventArgs e)
        {
            bool importerWasShown = false;

            if (_settings.HasPosition && IsSavedPositionVisible(_settings.X, _settings.Y))
                Location = new Point(_settings.X, _settings.Y);
            else
                MoveToBottomRight();

            string initial = FindInitialPackage();
            if (initial == null)
            {
                importerWasShown = true;
                ImportPackage();
                if (_package == null)
                {
                    Close();
                    return;
                }
            }
            else
            {
                try
                {
                    LoadPackage(initial, !PathsEqual(initial, PlayerSettings.CurrentPackPath));
                }
                catch (Exception error)
                {
                    MessageBox.Show("桌宠包无法打开：" + error.Message,
                        "桌宠播放器", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    importerWasShown = true;
                    ImportPackage();
                    if (_package == null)
                    {
                        Close();
                        return;
                    }
                }
            }

            if (_package != null &&
                !importerWasShown &&
                !String.Equals(_settings.ImportGuideVersion,
                    CurrentPlayerVersion, StringComparison.Ordinal))
            {
                importerWasShown = true;
                ImportPackage();
            }

            if (_package != null && importerWasShown)
            {
                _settings.ImportGuideVersion = CurrentPlayerVersion;
                _settings.Save();
            }

            ShowReadyTip();
        }

        private string FindInitialPackage()
        {
            if (!String.IsNullOrWhiteSpace(_requestedPack) && File.Exists(_requestedPack))
                return Path.GetFullPath(_requestedPack);
#if VISUAL_TEST
            string visualTestPack = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath), "visual-test.petpack");
            if (File.Exists(visualTestPack))
                return visualTestPack;
            return null;
#endif
            string executableDirectory = Path.GetDirectoryName(Application.ExecutablePath);
            string preferred = Path.Combine(executableDirectory, "加薪猫.petpack");
            if (File.Exists(preferred))
                return preferred;
            preferred = Path.Combine(executableDirectory, "default.petpack");
            if (File.Exists(preferred))
                return preferred;

            string[] packages = Directory.GetFiles(executableDirectory, "*.petpack");
            if (packages.Length > 0)
                return packages[0];

            if (!String.IsNullOrWhiteSpace(_settings.PackPath) && File.Exists(_settings.PackPath))
                return _settings.PackPath;
            return null;
        }

        private void ImportPackage()
        {
            while (!IsDisposed)
            {
                using (PackageImportForm dialog = new PackageImportForm(
                    _settings.PackPath))
                {
                    if (dialog.ShowDialog() != DialogResult.OK)
                        return;
                    if (TryLoadPackage(dialog.SelectedPath))
                        return;
                }
            }
        }

        private void OnPackageDragEnter(object sender, DragEventArgs e)
        {
            e.Effect = GetDroppedPackage(e.Data) == null
                ? DragDropEffects.None
                : DragDropEffects.Copy;
        }

        private void OnPackageDragDrop(object sender, DragEventArgs e)
        {
            string path = GetDroppedPackage(e.Data);
            if (path != null)
                TryLoadPackage(path);
        }

        private static string GetDroppedPackage(IDataObject data)
        {
            if (data == null || !data.GetDataPresent(DataFormats.FileDrop))
                return null;
            string[] files = data.GetData(DataFormats.FileDrop) as string[];
            if (files == null || files.Length != 1 || !File.Exists(files[0]))
                return null;
            string extension = Path.GetExtension(files[0]);
            if (!String.Equals(extension, ".petpack", StringComparison.OrdinalIgnoreCase) &&
                !String.Equals(extension, ".zip", StringComparison.OrdinalIgnoreCase))
                return null;
            return files[0];
        }

        private bool TryLoadPackage(string path)
        {
            try
            {
                LoadPackage(path, true);
                _trayIcon.BalloonTipTitle = "桌宠导入成功";
                _trayIcon.BalloonTipText = "已切换为“" + _package.Name +
                    "”。以后双击托盘图标即可更换桌宠。";
                _trayIcon.ShowBalloonTip(5000);
                return true;
            }
            catch (Exception error)
            {
                MessageBox.Show(
                    "这个桌宠包无法导入：\n\n" + error.Message +
                    "\n\n请重新从网站生成 .petpack，或选择另一个文件。",
                    "桌宠包导入失败",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning);
                return false;
            }
        }

        private void ShowReadyTip()
        {
            if (_package == null)
                return;
            _trayIcon.BalloonTipTitle = _package.Name + "正在运行";
            _trayIcon.BalloonTipText =
                "右键桌宠或双击右下角托盘图标，可以导入和更换桌宠包。";
            _trayIcon.ShowBalloonTip(4500);
        }

        private void LoadPackage(string path, bool storeAsCurrent)
        {
            PetPackage loaded = PetPackage.Load(path);
            string selectedPath = Path.GetFullPath(path);

            if (storeAsCurrent)
            {
                try
                {
                    Directory.CreateDirectory(PlayerSettings.DataDirectory);
                    string currentPath = PlayerSettings.CurrentPackPath;
                    if (!PathsEqual(selectedPath, currentPath))
                        File.Copy(selectedPath, currentPath, true);
                    selectedPath = currentPath;
                }
                catch (IOException)
                {
                    // The package beside the player is already valid and loaded.
                    // A stale or locked cache must never prevent it from running.
                }
                catch (UnauthorizedAccessException)
                {
                    // Keep using the original package when the cache is read-only.
                }
            }

            _animationTimer.Stop();
            PetPackage previous = _package;
            _package = loaded;
            if (previous != null)
                previous.Dispose();

            _settings.PackPath = selectedPath;
            Text = loaded.Name;
            string trayText = loaded.Name + " · 桌宠播放器";
            _trayIcon.Text = trayText.Length > 63 ? trayText.Substring(0, 63) : trayText;

            PopulateActionMenu();
            if (!_settings.HasSize || _settings.Size < 72 || _settings.Size > 320)
                SetPetSize(loaded.DefaultSize);
            SelectAction(0);
            _settings.Save();
        }

        private static bool PathsEqual(string first, string second)
        {
            if (String.IsNullOrWhiteSpace(first) || String.IsNullOrWhiteSpace(second))
                return false;
            return String.Equals(Path.GetFullPath(first).TrimEnd('\\'),
                Path.GetFullPath(second).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase);
        }

        private void PopulateActionMenu()
        {
            _actionsMenu.DropDownItems.Clear();
            for (int index = 0; index < _package.Actions.Count; index++)
            {
                int selectedIndex = index;
                ToolStripMenuItem item = new ToolStripMenuItem(_package.Actions[index].Name);
                item.Click += delegate
                {
                    SelectAction(selectedIndex);
                };
                _actionsMenu.DropDownItems.Add(item);
            }
        }

        private void AddSizeItem(ToolStripMenuItem parent, string title, int size)
        {
            ToolStripMenuItem item = new ToolStripMenuItem(title);
            item.Tag = size;
            item.Checked = size == _petSize;
            item.Click += delegate { SetPetSize(size); };
            _sizeItems.Add(item);
            parent.DropDownItems.Add(item);
        }

        private void SetPetSize(int size)
        {
            size = Math.Min(320, Math.Max(72, size));
            int oldRight = Right;
            int oldBottom = Bottom;
            _petSize = size;
            ClientSize = new Size(size, size);
            Location = new Point(oldRight - Width, oldBottom - Height);
            foreach (ToolStripMenuItem item in _sizeItems)
                item.Checked = (int)item.Tag == size;
            _settings.Size = size;
            _settings.HasSize = true;
            KeepInsideWorkingArea();
            RenderCurrentFrame();
        }

        private void MoveToBottomRight()
        {
            Rectangle workingArea = Screen.PrimaryScreen.WorkingArea;
            Location = new Point(workingArea.Right - Width - 18, workingArea.Bottom - Height - 18);
            RenderCurrentFrame();
        }

        private bool IsSavedPositionVisible(int x, int y)
        {
            Rectangle saved = new Rectangle(x, y, _petSize, _petSize);
            foreach (Screen screen in Screen.AllScreens)
            {
                if (screen.WorkingArea.IntersectsWith(saved))
                    return true;
            }
            return false;
        }

        private void KeepInsideWorkingArea()
        {
            Screen currentScreen = Screen.FromRectangle(Bounds);
            Rectangle area = currentScreen.WorkingArea;
            int x = Math.Min(Math.Max(Left, area.Left), area.Right - Width);
            int y = Math.Min(Math.Max(Top, area.Top), area.Bottom - Height);
            Location = new Point(x, y);
        }

        private void SelectRandomAction()
        {
            if (_package == null)
                return;
            int count = _package.Actions.Count;
            if (count <= 1)
            {
                SelectAction(0);
                return;
            }

            // Pick from every action while guaranteeing a visible switch.
            int next = _random.Next(count - 1);
            if (next >= _currentActionIndex)
                next++;
            SelectAction(next);
        }

        private void SelectAction(int index)
        {
            if (_package == null || index < 0 || index >= _package.Actions.Count)
                return;

            _animationTimer.Stop();
            _currentActionIndex = index;
            PetAction action = _package.Actions[index];
#if VISUAL_TEST
            Text = _package.Name + " · " + action.Name;
#endif
            action.Reset();
            RenderCurrentFrame();
            if (action.RequiresTimer)
            {
                _animationTimer.Interval = action.CurrentDelay;
                _animationTimer.Start();
            }
        }

        private void OnAnimationTick(object sender, EventArgs e)
        {
            if (_package == null)
                return;
            PetAction action = _package.Actions[_currentActionIndex];
            bool completed = action.MoveNext();
            if (completed && !action.Loop)
                action.Reset();
            RenderCurrentFrame();
            _animationTimer.Interval = action.CurrentDelay;
        }

        private void OnPointerDown(object sender, MouseEventArgs e)
        {
            if (e.Button != MouseButtons.Left)
                return;
            _pointerDown = true;
            _pointerMoved = false;
            _dragging = false;
            _pointerDownScreen = Cursor.Position;
            _windowDownLocation = Location;
            Capture = true;
        }

        private void OnPointerMove(object sender, MouseEventArgs e)
        {
            if (!_pointerDown || e.Button != MouseButtons.Left)
                return;
            Point current = Cursor.Position;
            int dx = current.X - _pointerDownScreen.X;
            int dy = current.Y - _pointerDownScreen.Y;
            int distanceSquared = (dx * dx) + (dy * dy);
            if (distanceSquared >= (ClickMovementTolerance * ClickMovementTolerance))
                _pointerMoved = true;
            if (!_dragging && ((dx * dx) + (dy * dy) <
                (DragActivationDistance * DragActivationDistance)))
                return;
            if (!_dragging)
                _dragging = true;
            Location = new Point(_windowDownLocation.X + dx, _windowDownLocation.Y + dy);
            RenderCurrentFrame();
        }

        private void OnPointerUp(object sender, MouseEventArgs e)
        {
            // Some layered-window/input combinations report MouseButtons.None on
            // release. _pointerDown is the reliable source of truth here; keeping
            // the button check could leave both clicks and drags stuck.
            if (!_pointerDown)
                return;
            Point current = Cursor.Position;
            int dx = current.X - _pointerDownScreen.X;
            int dy = current.Y - _pointerDownScreen.Y;
            bool moved = _pointerMoved || ((dx * dx) + (dy * dy) >=
                (ClickMovementTolerance * ClickMovementTolerance));
            if (!moved)
                SelectRandomAction();
            _pointerDown = false;
            _pointerMoved = false;
            _dragging = false;
            Capture = false;
            KeepInsideWorkingArea();
        }

        private void RenderCurrentFrame()
        {
            if (!IsHandleCreated || IsDisposed || _package == null)
                return;

            Image source = _package.Actions[_currentActionIndex].CurrentFrame.Image;
            using (Bitmap layer = new Bitmap(_petSize, _petSize, PixelFormat.Format32bppPArgb))
            {
                using (Graphics graphics = Graphics.FromImage(layer))
                {
                    graphics.Clear(Color.Transparent);
                    graphics.CompositingMode = CompositingMode.SourceCopy;
                    graphics.CompositingQuality = CompositingQuality.HighQuality;
                    graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
                    graphics.SmoothingMode = SmoothingMode.HighQuality;

                    double scale = Math.Min(_petSize / (double)source.Width, _petSize / (double)source.Height);
                    int drawWidth = Math.Max(1, (int)Math.Round(source.Width * scale));
                    int drawHeight = Math.Max(1, (int)Math.Round(source.Height * scale));
                    int drawX = (_petSize - drawWidth) / 2;
                    int drawY = (_petSize - drawHeight) / 2;
                    graphics.DrawImage(source, new Rectangle(drawX, drawY, drawWidth, drawHeight),
                        0, 0, source.Width, source.Height, GraphicsUnit.Pixel);
                }

                UpdateHitMask(layer);
                UpdateLayeredBitmap(layer);
            }
        }

        private void UpdateHitMask(Bitmap bitmap)
        {
            byte[] mask = new byte[_petSize * _petSize];
            Rectangle rectangle = new Rectangle(0, 0, bitmap.Width, bitmap.Height);
            BitmapData data = bitmap.LockBits(rectangle, ImageLockMode.ReadOnly, PixelFormat.Format32bppPArgb);
            try
            {
                byte[] row = new byte[Math.Abs(data.Stride)];
                for (int y = 0; y < bitmap.Height; y++)
                {
                    IntPtr rowPointer = IntPtr.Add(data.Scan0, y * data.Stride);
                    Marshal.Copy(rowPointer, row, 0, row.Length);
                    for (int x = 0; x < bitmap.Width; x++)
                        mask[(y * bitmap.Width) + x] = row[(x * 4) + 3];
                }
            }
            finally
            {
                bitmap.UnlockBits(data);
            }
            _hitMask = mask;
        }

        private void UpdateLayeredBitmap(Bitmap bitmap)
        {
            IntPtr screenDc = NativeMethods.GetDC(IntPtr.Zero);
            IntPtr memoryDc = NativeMethods.CreateCompatibleDC(screenDc);
            IntPtr bitmapHandle = IntPtr.Zero;
            IntPtr oldBitmap = IntPtr.Zero;
            try
            {
                bitmapHandle = bitmap.GetHbitmap(Color.FromArgb(0));
                oldBitmap = NativeMethods.SelectObject(memoryDc, bitmapHandle);
                NativePoint sourcePoint = new NativePoint(0, 0);
                NativePoint topPosition = new NativePoint(Left, Top);
                NativeSize size = new NativeSize(bitmap.Width, bitmap.Height);
                BlendFunction blend = new BlendFunction();
                blend.BlendOp = AcSrcOver;
                blend.SourceConstantAlpha = 255;
                blend.AlphaFormat = AcSrcAlpha;
                NativeMethods.UpdateLayeredWindow(Handle, screenDc, ref topPosition, ref size,
                    memoryDc, ref sourcePoint, 0, ref blend, UlwAlpha);
            }
            finally
            {
                if (oldBitmap != IntPtr.Zero)
                    NativeMethods.SelectObject(memoryDc, oldBitmap);
                if (bitmapHandle != IntPtr.Zero)
                    NativeMethods.DeleteObject(bitmapHandle);
                NativeMethods.DeleteDC(memoryDc);
                NativeMethods.ReleaseDC(IntPtr.Zero, screenDc);
            }
        }

        private void OnFormClosing(object sender, FormClosingEventArgs e)
        {
            _settings.X = Left;
            _settings.Y = Top;
            _settings.HasPosition = true;
            _settings.Size = _petSize;
            _settings.TopMost = TopMost;
            _settings.Save();
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _animationTimer.Stop();
                _animationTimer.Dispose();
                _trayIcon.Visible = false;
                _trayIcon.Dispose();
                if (_package != null)
                    _package.Dispose();
            }
            base.Dispose(disposing);
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct NativePoint
        {
            public int X;
            public int Y;
            public NativePoint(int x, int y) { X = x; Y = y; }
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct NativeSize
        {
            public int Width;
            public int Height;
            public NativeSize(int width, int height) { Width = width; Height = height; }
        }

        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        private struct BlendFunction
        {
            public byte BlendOp;
            public byte BlendFlags;
            public byte SourceConstantAlpha;
            public byte AlphaFormat;
        }

        private static class NativeMethods
        {
            [DllImport("user32.dll", SetLastError = true)]
            public static extern IntPtr GetDC(IntPtr window);
            [DllImport("user32.dll", SetLastError = true)]
            public static extern int ReleaseDC(IntPtr window, IntPtr dc);
            [DllImport("gdi32.dll", SetLastError = true)]
            public static extern IntPtr CreateCompatibleDC(IntPtr dc);
            [DllImport("gdi32.dll", SetLastError = true)]
            public static extern bool DeleteDC(IntPtr dc);
            [DllImport("gdi32.dll", SetLastError = true)]
            public static extern IntPtr SelectObject(IntPtr dc, IntPtr graphicsObject);
            [DllImport("gdi32.dll", SetLastError = true)]
            public static extern bool DeleteObject(IntPtr graphicsObject);
            [DllImport("user32.dll", SetLastError = true)]
            public static extern bool UpdateLayeredWindow(IntPtr window, IntPtr destinationDc,
                ref NativePoint destinationPoint, ref NativeSize size, IntPtr sourceDc,
                ref NativePoint sourcePoint, int colorKey, ref BlendFunction blend, int flags);
        }
    }

    internal sealed class PlayerSettings
    {
        public static readonly string DataDirectory = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DesktopPetPlayer");
        public static readonly string CurrentPackPath = Path.Combine(DataDirectory, "current.petpack");
        private static readonly string SettingsPath = Path.Combine(DataDirectory, "settings.ini");

        public bool HasPosition;
        public int X;
        public int Y;
        public int Size = 120;
        public bool HasSize;
        public bool TopMost = true;
        public string PackPath;
        public string ImportGuideVersion;

        public static PlayerSettings Load()
        {
            PlayerSettings settings = new PlayerSettings();
            if (!File.Exists(SettingsPath))
                return settings;
            try
            {
                foreach (string line in File.ReadAllLines(SettingsPath))
                {
                    int separator = line.IndexOf('=');
                    if (separator <= 0)
                        continue;
                    string key = line.Substring(0, separator);
                    string value = line.Substring(separator + 1);
                    int number;
                    bool flag;
                    if (key == "x" && Int32.TryParse(value, out number)) { settings.X = number; settings.HasPosition = true; }
                    else if (key == "y" && Int32.TryParse(value, out number)) { settings.Y = number; settings.HasPosition = true; }
                    else if (key == "size" && Int32.TryParse(value, out number)) { settings.Size = number; settings.HasSize = true; }
                    else if (key == "topmost" && Boolean.TryParse(value, out flag)) settings.TopMost = flag;
                    else if (key == "pack") settings.PackPath = value;
                    else if (key == "importGuideVersion") settings.ImportGuideVersion = value;
                }
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
            return settings;
        }

        public void Save()
        {
            try
            {
                Directory.CreateDirectory(DataDirectory);
                File.WriteAllLines(SettingsPath, new string[]
                {
                    "x=" + X,
                    "y=" + Y,
                    "size=" + Size,
                    "topmost=" + TopMost,
                    "pack=" + (PackPath ?? String.Empty),
                    "importGuideVersion=" + (ImportGuideVersion ?? String.Empty)
                });
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
    }

    [DataContract]
    internal sealed class PetManifest
    {
        [DataMember(Name = "formatVersion", IsRequired = true)] public int FormatVersion { get; set; }
        [DataMember(Name = "id", IsRequired = true)] public string Id { get; set; }
        [DataMember(Name = "name", IsRequired = true)] public string Name { get; set; }
        [DataMember(Name = "defaultSize", IsRequired = true)] public int DefaultSize { get; set; }
        [DataMember(Name = "icon", IsRequired = true)] public string Icon { get; set; }
        [DataMember(Name = "actions", IsRequired = true)] public List<ActionManifest> Actions { get; set; }
    }

    [DataContract]
    internal sealed class ActionManifest
    {
        [DataMember(Name = "name", IsRequired = true)] public string Name { get; set; }
        [DataMember(Name = "role", IsRequired = true)] public string Role { get; set; }
        [DataMember(Name = "loop", IsRequired = true)] public bool Loop { get; set; }
        [DataMember(Name = "frames", IsRequired = true)] public List<FrameManifest> Frames { get; set; }
    }

    [DataContract]
    internal sealed class FrameManifest
    {
        [DataMember(Name = "file", IsRequired = true)] public string File { get; set; }
        [DataMember(Name = "duration", IsRequired = true)] public int Duration { get; set; }
    }

    internal sealed class PetPackage : IDisposable
    {
        private const long MaxPackBytes = 48L * 1024 * 1024;
        private const long MaxUncompressedBytes = 256L * 1024 * 1024;
        private const long MaxEntryBytes = 16L * 1024 * 1024;
        private const long MaxTotalPixels = 48000000;

        public string Name { get; private set; }
        public int DefaultSize { get; private set; }
        public List<PetAction> Actions { get; private set; }

        private PetPackage()
        {
            Actions = new List<PetAction>();
        }

        public static PetPackage Load(string path)
        {
            FileInfo file = new FileInfo(path);
            if (!file.Exists)
                throw new InvalidDataException("文件不存在。");
            if (file.Length < 1 || file.Length > MaxPackBytes)
                throw new InvalidDataException("资源包大小不符合限制。");

            PetPackage package = new PetPackage();
            try
            {
                using (FileStream stream = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.Read))
                using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read, false))
                {
                    Dictionary<string, ZipArchiveEntry> entries = new Dictionary<string, ZipArchiveEntry>(StringComparer.OrdinalIgnoreCase);
                    long totalUncompressed = 0;
                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        string name = NormalizeEntryName(entry.FullName);
                        totalUncompressed += entry.Length;
                        if (entry.Length > MaxEntryBytes || totalUncompressed > MaxUncompressedBytes)
                            throw new InvalidDataException("资源包解压后过大。");
                        if (entries.ContainsKey(name))
                            throw new InvalidDataException("资源包包含重复文件。");
                        entries.Add(name, entry);
                    }

                    ZipArchiveEntry manifestEntry;
                    if (!entries.TryGetValue("pet.json", out manifestEntry) || manifestEntry.Length > 1024 * 1024)
                        throw new InvalidDataException("缺少有效的 pet.json。");

                    PetManifest manifest;
                    using (Stream manifestStream = manifestEntry.Open())
                    {
                        DataContractJsonSerializer serializer = new DataContractJsonSerializer(typeof(PetManifest));
                        manifest = serializer.ReadObject(manifestStream) as PetManifest;
                    }
                    ValidateManifest(manifest);

                    package.Name = manifest.Name.Trim();
                    package.DefaultSize = Math.Min(320, Math.Max(72, manifest.DefaultSize));
                    long totalPixels = 0;

                    foreach (ActionManifest actionManifest in manifest.Actions)
                    {
                        PetAction action = new PetAction(actionManifest.Name.Trim(), actionManifest.Role, actionManifest.Loop);
                        foreach (FrameManifest frameManifest in actionManifest.Frames)
                        {
                            string frameName = NormalizeEntryName(frameManifest.File);
                            if (!frameName.StartsWith("assets/", StringComparison.OrdinalIgnoreCase))
                                throw new InvalidDataException("帧文件必须位于 assets 目录。");
                            ZipArchiveEntry frameEntry;
                            if (!entries.TryGetValue(frameName, out frameEntry))
                                throw new InvalidDataException("资源包缺少动画帧。");

                            MemoryStream frameStream = ReadEntry(frameEntry, MaxEntryBytes);
                            Image image;
                            try
                            {
                                image = Image.FromStream(frameStream, true, true);
                                image.RotateFlip(RotateFlipType.Rotate180FlipNone);
                                image.RotateFlip(RotateFlipType.Rotate180FlipNone);
                            }
                            catch
                            {
                                frameStream.Dispose();
                                throw new InvalidDataException("动画帧不是有效图片。");
                            }
                            if (image.Width < 1 || image.Height < 1 || image.Width > 2048 || image.Height > 2048)
                            {
                                image.Dispose();
                                frameStream.Dispose();
                                throw new InvalidDataException("动画帧尺寸超出限制。");
                            }
                            totalPixels += (long)image.Width * image.Height;
                            if (totalPixels > MaxTotalPixels)
                            {
                                image.Dispose();
                                frameStream.Dispose();
                                throw new InvalidDataException("资源包总像素超出限制。");
                            }
                            action.Frames.Add(new PetFrame(frameStream, image,
                                Math.Min(2000, Math.Max(20, frameManifest.Duration))));
                        }
                        package.Actions.Add(action);
                    }
                }
                return package;
            }
            catch
            {
                package.Dispose();
                throw;
            }
        }

        private static void ValidateManifest(PetManifest manifest)
        {
            if (manifest == null || manifest.FormatVersion != 1)
                throw new InvalidDataException("不支持的桌宠包版本。");
            if (String.IsNullOrWhiteSpace(manifest.Name) || manifest.Name.Length > 32)
                throw new InvalidDataException("桌宠名称无效。");
            if (manifest.Actions == null || manifest.Actions.Count < 1 || manifest.Actions.Count > 48)
                throw new InvalidDataException("动作数量必须在 1～48 个。");
            foreach (ActionManifest action in manifest.Actions)
            {
                if (action == null || String.IsNullOrWhiteSpace(action.Name) || action.Name.Length > 24)
                    throw new InvalidDataException("动作名称无效。");
                if (action.Frames == null || action.Frames.Count < 1 || action.Frames.Count > 120)
                    throw new InvalidDataException("单个动作必须包含 1～120 帧。");
            }
        }

        private static string NormalizeEntryName(string name)
        {
            if (String.IsNullOrWhiteSpace(name))
                throw new InvalidDataException("资源包包含空文件名。");
            string normalized = name.Replace('\\', '/').TrimStart('/');
            if (normalized.Contains("../") || normalized == ".." || normalized.Contains(":"))
                throw new InvalidDataException("资源包包含非法路径。");
            return normalized;
        }

        private static MemoryStream ReadEntry(ZipArchiveEntry entry, long limit)
        {
            MemoryStream output = new MemoryStream((int)Math.Min(entry.Length, Int32.MaxValue));
            using (Stream input = entry.Open())
            {
                byte[] buffer = new byte[81920];
                long total = 0;
                int read;
                while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
                {
                    total += read;
                    if (total > limit)
                    {
                        output.Dispose();
                        throw new InvalidDataException("资源文件过大。");
                    }
                    output.Write(buffer, 0, read);
                }
            }
            output.Position = 0;
            return output;
        }

        public void Dispose()
        {
            foreach (PetAction action in Actions)
                action.Dispose();
            Actions.Clear();
        }
    }

    internal sealed class PetAction : IDisposable
    {
        private int _frameIndex;
        public string Name { get; private set; }
        public string Role { get; private set; }
        public bool Loop { get; private set; }
        public List<PetFrame> Frames { get; private set; }
        public PetFrame CurrentFrame { get { return Frames[_frameIndex]; } }
        public int CurrentDelay { get { return CurrentFrame.Duration; } }
        public bool RequiresTimer { get { return Frames.Count > 1 || !Loop; } }

        public PetAction(string name, string role, bool loop)
        {
            Name = name;
            Role = String.IsNullOrWhiteSpace(role) ? "custom" : role;
            Loop = loop;
            Frames = new List<PetFrame>();
        }

        public void Reset() { _frameIndex = 0; }

        public bool MoveNext()
        {
            if (_frameIndex + 1 < Frames.Count)
            {
                _frameIndex++;
                return false;
            }
            if (Loop)
            {
                _frameIndex = 0;
                return false;
            }
            return true;
        }

        public void Dispose()
        {
            foreach (PetFrame frame in Frames)
                frame.Dispose();
            Frames.Clear();
        }
    }

    internal sealed class PetFrame : IDisposable
    {
        private readonly MemoryStream _stream;
        public Image Image { get; private set; }
        public int Duration { get; private set; }

        public PetFrame(MemoryStream stream, Image image, int duration)
        {
            _stream = stream;
            Image = image;
            Duration = duration;
        }

        public void Dispose()
        {
            if (Image != null)
            {
                Image.Dispose();
                Image = null;
            }
            _stream.Dispose();
        }
    }
}
