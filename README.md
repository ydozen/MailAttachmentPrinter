# メール受信、添付ファイル自動印刷プログラム

- Linux環境、Pyothon3の環境で動作します。
- mail_config.Jsonに設定したメール、添付ファイル保存パス、プリンターを設定します。
- プログラムは常駐しメールを受信次第印刷します。
- 動作ログは/var/log/mail_processor.logを参照してください。

以下に、サービスの設定と動作確認についての手順をテキストで示します。

### サービスの設定と動作確認手順

1. **サービスファイルの作成**

   `/etc/systemd/system/mail_attachment_printer.service` という名前のファイルを作成し、以下の内容で設定します。このファイルは、プログラムをシステムサービスとして管理するための設定を含んでいます。

  mail_attachment_printer.service
   [Unit]
   Description=Mail Attachment Printer Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /path/to/mail_processor.py
   WorkingDirectory=/path/to/directory_containing_script
   User=your_user
   Group=your_group
   Restart=always
   StandardOutput=append:/var/log/mail_processor.log
   StandardError=append:/var/log/mail_processor.log

   [Install]
   WantedBy=multi-user.target
   ```

   - **ExecStart**: 実行するコマンドのパスを指定します。ここでは Python スクリプトのパスを指定しています。
   - **WorkingDirectory**: スクリプトが実行される作業ディレクトリを指定します。
   - **User** と **Group**: スクリプトを実行するユーザーとグループを指定します。
   - **Restart**: サービスが停止した場合に自動的に再起動する設定です。
   - **StandardOutput** と **StandardError**: ログの出力先を指定します。ここではログを `/var/log/mail_processor.log` に追記します。

2. **サービスの有効化と起動**

   サービスをシステムに登録して、自動起動するように設定します。

   sudo systemctl enable mail_attachment_printer.service
   sudo systemctl start mail_attachment_printer.service

   - **enable**: システム起動時にサービスが自動的に起動するように設定します。
   - **start**: サービスを手動で起動します。

3. **サービスの状態確認**

   サービスが正しく動作しているかどうかを確認します。

   sudo systemctl status mail_attachment_printer.service

   - **status**: サービスの現在の状態やログを確認します。動作中であれば `Active: active (running)` と表示されます。

4. **ログファイルの確認**

   サービスが出力するログファイルを確認し、動作ログやエラーメッセージをチェックします。

   sudo tail -f /var/log/mail_processor.log

   - **tail -f**: ログファイルの最後の部分をリアルタイムで表示します。サービスの動作状況を監視するのに便利です。

5. **サービスの停止と無効化**

   サービスを停止し、システム起動時の自動起動を無効化する場合は以下のコマンドを使用します。

   sudo systemctl stop mail_attachment_printer.service
   sudo systemctl disable mail_attachment_printer.service

   - **stop**: サービスを停止します。
   - **disable**: システム起動時の自動起動を無効化します。

これらの手順に従うことで、Pythonスクリプトをシステムサービスとして管理し、正常に動作しているかどうかを確認することができます。