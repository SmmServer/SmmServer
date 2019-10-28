using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace SmmServer
{
    public partial class SmmServer : Form
    {
        private List<Process> _processes = new List<Process>();
        private List<StreamWriter> _logStreams = new List<StreamWriter>();

#if DEBUG
        private string _pythonDir = @"d:\WiiU\SmmServerFinal\python-3.7.5-embed-win32";
        private string _caddyDir = @"d:\WiiU\SmmServerFinal\Caddy";
        private string _nintendoClientsDir = @"c:\CodeBlocks\NintendoClients";
        private string _cemuDir = @"d:\WiiU\cemu_1.15.17";
#else
        private string _pythonDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "python-3.7.5-embed-win32");
        private string _caddyDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Caddy");
        private string _nintendoClientsDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "NintendoClients");
        private string _cemuDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Cemu");
#endif
        private string _pidsFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "SmmServer.pids");

        public SmmServer()
        {
            InitializeComponent();
            Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            tabControlProcesses.SelectedIndexChanged += TabControlProcesses_SelectedIndexChanged;
        }

        private void TabControlProcesses_SelectedIndexChanged(object sender, EventArgs e)
        {
            tabControlProcesses.SelectedTab.Text = tabControlProcesses.SelectedTab.Text.TrimEnd('*');
        }

        private void tabUpdated(TabPage tab)
        {
            if (tabControlProcesses.SelectedTab != tab)
            {
                if (!tab.Text.EndsWith("*"))
                    tab.Text += "*";
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            stopProcesses();
            base.OnClosed(e);
        }

        private delegate void AppendLine(string line);

        private void doProcess(string filename, string arguments, string workingDir, AppendLine output)
        {
            var process = Process.Start(new ProcessStartInfo
            {
                FileName = filename,
                Arguments = arguments,
                WorkingDirectory = workingDir,
                UseShellExecute = false,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                CreateNoWindow = true,
            });
            process.OutputDataReceived += (sender, args) => output(string.IsNullOrEmpty(args.Data) ? "" : args.Data);
            process.ErrorDataReceived += (sender, args) => output(string.IsNullOrEmpty(args.Data) ? "" : args.Data);
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            _processes.Add(process);
            var pids = new List<string>();
            if (File.Exists(_pidsFile))
                pids = File.ReadAllLines(_pidsFile).ToList();
            pids.Add(process.Id.ToString());
            File.WriteAllLines(_pidsFile, pids.ToArray());
        }

        private void python(string script, AppendLine output)
        {
            var workingDir = Path.GetDirectoryName(script);
            Environment.SetEnvironmentVariable("PYTHONHOME", _pythonDir);
            var filename = Path.Combine(_pythonDir, "python.exe");
            doProcess(filename, $"\"{script}\"", workingDir, output);
        }

        private void exec(string exe, AppendLine output)
        {
            var workingDir = Path.GetDirectoryName(exe);
            doProcess(exe, "", workingDir, output);
        }

        private void stopProcesses()
        {
            foreach (var process in _processes)
            {
                try
                {
                    process.Kill();
                    process.CancelOutputRead();
                    process.CancelErrorRead();
                    process.WaitForExit();
                }
                catch
                {
                }
            }
            _processes.Clear();

            if (File.Exists(_pidsFile))
                File.Delete(_pidsFile);

            foreach (var logStream in _logStreams)
                logStream.Close();
            _logStreams.Clear();
        }

        AppendLine makeControlOutput(TabPage tab, TextBox textBox)
        {
            var logStream = new StreamWriter(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, tab.Text.TrimEnd('*') + ".log"), true);
            _logStreams.Add(logStream);
            return line => textBox.InvokeIfRequired(tb =>
            {
                var newline = line + "\n";
                logStream.Write(newline);
                tb.AppendText(newline);
                tabUpdated(tab);
            });
        }

        private void buttonStart_Click(object sender, EventArgs e)
        {
            if (_processes.Count == 0)
            {
                buttonStart.Enabled = false;
                if (File.Exists(_pidsFile))
                {
                    var pids = File.ReadAllLines(_pidsFile);
                    var processNames = new HashSet<string>(new[] { "python", "caddy", "Pretendo++" });
                    foreach (var pidStr in pids)
                    {
                        int pid;
                        if (int.TryParse(pidStr, out pid))
                        {
                            try
                            {
                                var process = Process.GetProcessById(pid);
                                if (processNames.Contains(process.ProcessName))
                                {
                                    textBoxSmm.AppendText($"Killing {process.ProcessName} ({pid})\n");
                                    process.Kill();
                                }
                            }
                            catch
                            {
                            }
                        }
                    }
                    File.Delete(_pidsFile);
                }

                python(Path.Combine(_nintendoClientsDir, "example_smm_server.py"), makeControlOutput(tabPageSmm, textBoxSmm));
                python(Path.Combine(_nintendoClientsDir, "example_friend_server.py"), makeControlOutput(tabPageFriends, textBoxFriends));
                exec(Path.Combine(_caddyDir, "caddy.exe"), makeControlOutput(tabPageCaddy, textBoxCaddy));
                exec(Path.Combine(_nintendoClientsDir, "Pretendo++.exe"), makeControlOutput(tabPagePretendo, textBoxPretendo));
                buttonStart.Text = "Started";
            }
        }

        private void button1_Click(object sender, EventArgs e)
        {
            tabUpdated(tabPageSmm);
        }

        private void buttonClear_Click(object sender, EventArgs e)
        {
            void clearTab(TabPage tab, TextBox textBox)
            {
                textBox.Clear();
                tab.Text = tab.Text.TrimEnd('*');
            }

            clearTab(tabPageSmm, textBoxSmm);
            clearTab(tabPageFriends, textBoxFriends);
            clearTab(tabPagePretendo, textBoxPretendo);
            clearTab(tabPageCaddy, textBoxCaddy);

            foreach (var logStream in _logStreams)
                logStream.Flush();
        }

        private void buttonCemu_Click(object sender, EventArgs e)
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = Path.Combine(_cemuDir, "Cemu.exe"),
                WorkingDirectory = _cemuDir,
            });
        }

        private void linkLabelWebsite_LinkClicked(object sender, LinkLabelLinkClickedEventArgs e)
        {
            Process.Start("https://smmserver.github.io");
        }
    }
}
