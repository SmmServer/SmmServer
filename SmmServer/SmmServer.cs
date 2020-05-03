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
using System.Threading;

namespace SmmServer
{
    public partial class SmmServer : Form
    {
        private List<Process> _processes = new List<Process>();
        private Dictionary<string, StreamWriter> _logStreams = new Dictionary<string, StreamWriter>();

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

        public delegate void AppendLine(string line);

        private Process doProcess(string filename, string arguments, string workingDir, AppendLine output)
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
            return process;
        }

        private Process python(string script, AppendLine output)
        {
            var workingDir = Path.GetDirectoryName(script);
            Environment.SetEnvironmentVariable("PYTHONHOME", _pythonDir);
            var filename = Path.Combine(_pythonDir, "python.exe");
            return doProcess(filename, $"\"{script}\"", workingDir, output);
        }

        private Process exec(string exe, AppendLine output)
        {
            var workingDir = Path.GetDirectoryName(exe);
            return doProcess(exe, "", workingDir, output);
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
                logStream.Value.Close();
            _logStreams.Clear();
        }

        StreamWriter findOrCreateStream(TabPage tab)
        {
            var logFile = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, tab.Text.TrimEnd('*') + ".log");
            if (!_logStreams.ContainsKey(logFile))
            {
                var logStream = new StreamWriter(logFile, true);
                logStream.AutoFlush = true;
                _logStreams.Add(logFile, logStream);
            }
            return _logStreams[logFile];
        }

        AppendLine makeControlOutput(TabPage tab, TextBox textBox)
        {
            var logStream = findOrCreateStream(tab);
            return line => textBox.InvokeIfRequired(tb =>
            {
                var newline = line.Replace("\r", "").Replace("\n", "\r\n") + "\r\n";
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
                                    textBoxSmm.AppendText($"Killing {process.ProcessName} ({pid})\r\n");
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

                // Enable debug button after 2 seconds
                new Thread(() =>
                {
                    Thread.Sleep(2000);
                    buttonDebug.InvokeIfRequired(button => button.Enabled = true);
                }).Start();
            }
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

        private void buttonDebug_Click(object sender, EventArgs e)
        {
            buttonDebug.Enabled = false;
            tabControlProcesses.SelectedTab = tabPageDebug;
            var debugOutput = makeControlOutput(tabPageDebug, textBoxDebug);
            new Thread(() =>
            {
                debugOutput("[Debug] Wait until you see 'Finished!' and the debug button is re-enabled\r\n");

                debugOutput("[Debug] Attempting NEX friend service login...");
                python(Path.Combine(_nintendoClientsDir, "example_friend_login.py"), debugOutput).WaitForExit();

                debugOutput("[Debug] Attempting NEX SMM service login...");
                python(Path.Combine(_nintendoClientsDir, "example_smm_login.py"), debugOutput).WaitForExit();

                debugOutput("[Debug] Attempting HTTPS connection...");
                SslTcpClient.Output = debugOutput;
                SslTcpClient.RunClient("127.0.0.1", "account.nintendo.net");
                debugOutput("");

                debugOutput("[Debug] Attempting full service test...");
                python(Path.Combine(_nintendoClientsDir, "smm_example_public.py"), debugOutput).WaitForExit();

                debugOutput("[Debug] Finished, please send all the .log files!");
                buttonDebug.InvokeIfRequired(button => button.Enabled = true);
            }).Start();
        }
    }
}
