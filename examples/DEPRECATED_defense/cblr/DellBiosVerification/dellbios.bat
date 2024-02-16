mkdir c:\tmpbios
del BiosImages.zip
"C:\Program Files\Dell\BiosVerification\Dell.TrustedDevice.Service.Console.exe" -exportall -export c:\tmpbios
powershell.exe -ExecutionPolicy Bypass Compress-Archive -Path c:\tmpbios\*.* -DestinationPath BiosImages.zip -Force