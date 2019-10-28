namespace SmmServer
{
    partial class SmmServer
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            this.buttonStart = new System.Windows.Forms.Button();
            this.tabControlProcesses = new System.Windows.Forms.TabControl();
            this.tabPageSmm = new System.Windows.Forms.TabPage();
            this.tabPageFriends = new System.Windows.Forms.TabPage();
            this.tabPagePretendo = new System.Windows.Forms.TabPage();
            this.tabPageCaddy = new System.Windows.Forms.TabPage();
            this.textBoxSmm = new System.Windows.Forms.TextBox();
            this.textBoxFriends = new System.Windows.Forms.TextBox();
            this.textBoxPretendo = new System.Windows.Forms.TextBox();
            this.textBoxCaddy = new System.Windows.Forms.TextBox();
            this.buttonClear = new System.Windows.Forms.Button();
            this.buttonCemu = new System.Windows.Forms.Button();
            this.tabControlProcesses.SuspendLayout();
            this.tabPageSmm.SuspendLayout();
            this.tabPageFriends.SuspendLayout();
            this.tabPagePretendo.SuspendLayout();
            this.tabPageCaddy.SuspendLayout();
            this.SuspendLayout();
            // 
            // buttonStart
            // 
            this.buttonStart.Location = new System.Drawing.Point(12, 12);
            this.buttonStart.Name = "buttonStart";
            this.buttonStart.Size = new System.Drawing.Size(75, 23);
            this.buttonStart.TabIndex = 0;
            this.buttonStart.Text = "&Start";
            this.buttonStart.UseVisualStyleBackColor = true;
            this.buttonStart.Click += new System.EventHandler(this.buttonStart_Click);
            // 
            // tabControlProcesses
            // 
            this.tabControlProcesses.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.tabControlProcesses.Controls.Add(this.tabPageSmm);
            this.tabControlProcesses.Controls.Add(this.tabPageFriends);
            this.tabControlProcesses.Controls.Add(this.tabPagePretendo);
            this.tabControlProcesses.Controls.Add(this.tabPageCaddy);
            this.tabControlProcesses.Location = new System.Drawing.Point(12, 41);
            this.tabControlProcesses.Name = "tabControlProcesses";
            this.tabControlProcesses.SelectedIndex = 0;
            this.tabControlProcesses.Size = new System.Drawing.Size(776, 397);
            this.tabControlProcesses.TabIndex = 1;
            // 
            // tabPageSmm
            // 
            this.tabPageSmm.Controls.Add(this.textBoxSmm);
            this.tabPageSmm.Location = new System.Drawing.Point(4, 22);
            this.tabPageSmm.Name = "tabPageSmm";
            this.tabPageSmm.Padding = new System.Windows.Forms.Padding(3);
            this.tabPageSmm.Size = new System.Drawing.Size(768, 371);
            this.tabPageSmm.TabIndex = 0;
            this.tabPageSmm.Text = "NEX (SMM)";
            this.tabPageSmm.UseVisualStyleBackColor = true;
            // 
            // tabPageFriends
            // 
            this.tabPageFriends.Controls.Add(this.textBoxFriends);
            this.tabPageFriends.Location = new System.Drawing.Point(4, 22);
            this.tabPageFriends.Name = "tabPageFriends";
            this.tabPageFriends.Padding = new System.Windows.Forms.Padding(3);
            this.tabPageFriends.Size = new System.Drawing.Size(768, 371);
            this.tabPageFriends.TabIndex = 1;
            this.tabPageFriends.Text = "NEX (Friends)";
            this.tabPageFriends.UseVisualStyleBackColor = true;
            // 
            // tabPagePretendo
            // 
            this.tabPagePretendo.Controls.Add(this.textBoxPretendo);
            this.tabPagePretendo.Location = new System.Drawing.Point(4, 22);
            this.tabPagePretendo.Name = "tabPagePretendo";
            this.tabPagePretendo.Padding = new System.Windows.Forms.Padding(3);
            this.tabPagePretendo.Size = new System.Drawing.Size(768, 371);
            this.tabPagePretendo.TabIndex = 2;
            this.tabPagePretendo.Text = "Pretendo++";
            this.tabPagePretendo.UseVisualStyleBackColor = true;
            // 
            // tabPageCaddy
            // 
            this.tabPageCaddy.Controls.Add(this.textBoxCaddy);
            this.tabPageCaddy.Location = new System.Drawing.Point(4, 22);
            this.tabPageCaddy.Name = "tabPageCaddy";
            this.tabPageCaddy.Padding = new System.Windows.Forms.Padding(3);
            this.tabPageCaddy.Size = new System.Drawing.Size(768, 371);
            this.tabPageCaddy.TabIndex = 3;
            this.tabPageCaddy.Text = "Caddy";
            this.tabPageCaddy.UseVisualStyleBackColor = true;
            // 
            // textBoxSmm
            // 
            this.textBoxSmm.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.textBoxSmm.Font = new System.Drawing.Font("Lucida Console", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.textBoxSmm.Location = new System.Drawing.Point(0, 0);
            this.textBoxSmm.Multiline = true;
            this.textBoxSmm.Name = "textBoxSmm";
            this.textBoxSmm.ReadOnly = true;
            this.textBoxSmm.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxSmm.Size = new System.Drawing.Size(768, 371);
            this.textBoxSmm.TabIndex = 0;
            this.textBoxSmm.WordWrap = false;
            // 
            // textBoxFriends
            // 
            this.textBoxFriends.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.textBoxFriends.Font = new System.Drawing.Font("Lucida Console", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.textBoxFriends.Location = new System.Drawing.Point(0, 0);
            this.textBoxFriends.Multiline = true;
            this.textBoxFriends.Name = "textBoxFriends";
            this.textBoxFriends.ReadOnly = true;
            this.textBoxFriends.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxFriends.Size = new System.Drawing.Size(768, 371);
            this.textBoxFriends.TabIndex = 1;
            this.textBoxFriends.WordWrap = false;
            // 
            // textBoxPretendo
            // 
            this.textBoxPretendo.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.textBoxPretendo.Font = new System.Drawing.Font("Lucida Console", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.textBoxPretendo.Location = new System.Drawing.Point(0, 0);
            this.textBoxPretendo.Multiline = true;
            this.textBoxPretendo.Name = "textBoxPretendo";
            this.textBoxPretendo.ReadOnly = true;
            this.textBoxPretendo.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxPretendo.Size = new System.Drawing.Size(768, 371);
            this.textBoxPretendo.TabIndex = 1;
            this.textBoxPretendo.WordWrap = false;
            // 
            // textBoxCaddy
            // 
            this.textBoxCaddy.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom) 
            | System.Windows.Forms.AnchorStyles.Left) 
            | System.Windows.Forms.AnchorStyles.Right)));
            this.textBoxCaddy.Font = new System.Drawing.Font("Lucida Console", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.textBoxCaddy.Location = new System.Drawing.Point(0, 0);
            this.textBoxCaddy.Multiline = true;
            this.textBoxCaddy.Name = "textBoxCaddy";
            this.textBoxCaddy.ReadOnly = true;
            this.textBoxCaddy.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxCaddy.Size = new System.Drawing.Size(768, 371);
            this.textBoxCaddy.TabIndex = 1;
            this.textBoxCaddy.WordWrap = false;
            // 
            // buttonClear
            // 
            this.buttonClear.Location = new System.Drawing.Point(174, 12);
            this.buttonClear.Name = "buttonClear";
            this.buttonClear.Size = new System.Drawing.Size(75, 23);
            this.buttonClear.TabIndex = 3;
            this.buttonClear.Text = "Clear &logs";
            this.buttonClear.UseVisualStyleBackColor = true;
            this.buttonClear.Click += new System.EventHandler(this.buttonClear_Click);
            // 
            // buttonCemu
            // 
            this.buttonCemu.Location = new System.Drawing.Point(93, 12);
            this.buttonCemu.Name = "buttonCemu";
            this.buttonCemu.Size = new System.Drawing.Size(75, 23);
            this.buttonCemu.TabIndex = 4;
            this.buttonCemu.Text = "Start &Cemu";
            this.buttonCemu.UseVisualStyleBackColor = true;
            this.buttonCemu.Click += new System.EventHandler(this.buttonCemu_Click);
            // 
            // SmmServer
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(800, 450);
            this.Controls.Add(this.buttonCemu);
            this.Controls.Add(this.buttonClear);
            this.Controls.Add(this.tabControlProcesses);
            this.Controls.Add(this.buttonStart);
            this.Name = "SmmServer";
            this.Text = "SmmServer v0.1";
            this.tabControlProcesses.ResumeLayout(false);
            this.tabPageSmm.ResumeLayout(false);
            this.tabPageSmm.PerformLayout();
            this.tabPageFriends.ResumeLayout(false);
            this.tabPageFriends.PerformLayout();
            this.tabPagePretendo.ResumeLayout(false);
            this.tabPagePretendo.PerformLayout();
            this.tabPageCaddy.ResumeLayout(false);
            this.tabPageCaddy.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button buttonStart;
        private System.Windows.Forms.TabControl tabControlProcesses;
        private System.Windows.Forms.TabPage tabPageSmm;
        private System.Windows.Forms.TabPage tabPageFriends;
        private System.Windows.Forms.TabPage tabPagePretendo;
        private System.Windows.Forms.TabPage tabPageCaddy;
        private System.Windows.Forms.TextBox textBoxSmm;
        private System.Windows.Forms.TextBox textBoxFriends;
        private System.Windows.Forms.TextBox textBoxPretendo;
        private System.Windows.Forms.TextBox textBoxCaddy;
        private System.Windows.Forms.Button buttonClear;
        private System.Windows.Forms.Button buttonCemu;
    }
}

