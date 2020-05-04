using System;
using System.Collections;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Text;
using System.Security.Cryptography.X509Certificates;
using System.IO;

namespace SmmServer
{
    public class SslTcpClient
    {
        private static Hashtable certificateErrors = new Hashtable();
        public static SmmServer.AppendLine Output;

        // The following method is invoked by the RemoteCertificateValidationDelegate.
        public static bool ValidateServerCertificate(
              object sender,
              X509Certificate certificate,
              X509Chain chain,
              SslPolicyErrors sslPolicyErrors)
        {
            if (sslPolicyErrors == SslPolicyErrors.None)
                return true;

            Output($"\r\nSSL Certificate:\r\n{certificate}");

            var isExpectedCert = certificate.GetCertHashString() == "A9BB409980B3A4110CFFE482847A510848B1E1EC";

            return isExpectedCert;
        }

        public static void RunClient(string machineName, string serverName)
        {
            TcpClient client = null;
            try
            {
                // Create a TCP/IP client socket.
                // machineName is the host running the server application.
                client = new TcpClient(machineName, 443);
                Output("TCP Client connected.");
                // Create an SSL stream that will close the client's stream.
                SslStream sslStream = new SslStream(
                    client.GetStream(),
                    false,
                    new RemoteCertificateValidationCallback(ValidateServerCertificate),
                    null
                    );
                // The server name must match the name on the server certificate.
                sslStream.AuthenticateAsClient(serverName, null, (SslProtocols)0x00000C00, false);
                // Encode a test message into a byte array.
                // Signal the end of the message using the "<EOF>".
                byte[] messsage = Encoding.UTF8.GetBytes("GET /ping HTTP/1.1\r\nHost: account.nintendo.net\r\n\r\n");
                // Send hello message to the server. 
                sslStream.Write(messsage);
                sslStream.Flush();
                // Read message from the server.
                string serverMessage = ReadMessage(sslStream);
                Output($"Server response:\r\n{serverMessage}");
                // Close the client connection.
                client.Close();
                Output("\r\nTCP Client closed.");
            }
            catch (Exception e)
            {
                Output($"Exception: {e.Message}");
                if (e.InnerException != null)
                {
                    Output($"Inner exception: {e.InnerException.Message}");
                }
                Output("Authentication failed - closing the connection.");
                if (client != null)
                    client.Close();
            }
        }

        static string ReadMessage(SslStream sslStream)
        {
            byte[] buffer = new byte[2048];
            StringBuilder messageData = new StringBuilder();
            int bytes = -1;
            do
            {
                bytes = sslStream.Read(buffer, 0, buffer.Length);

                // Use Decoder class to convert from bytes to UTF8
                // in case a character spans two buffers.
                Decoder decoder = Encoding.UTF8.GetDecoder();
                char[] chars = new char[decoder.GetCharCount(buffer, 0, bytes)];
                decoder.GetChars(buffer, 0, bytes, chars, 0);
                messageData.Append(chars);
                // Check for EOF.
                if (messageData.ToString().IndexOf("\r\n\r\n") != -1)
                {
                    break;
                }
            } while (bytes != 0);

            return messageData.ToString();
        }
    }
}
