# Python-File-Sharing-APP
Large Efficient Flexible and Trusty (LEFT) Files Sharing application. 

  This application is based on TCP protocol and achieved using Python socket programming. The application adopts multi-process and multi-threaded technique to support multi-users and realize high efficiency. 
  The primary purpose of the application is to enable multiple users to share files on a server. Users can upload files and also automatically download files from other users who are connected to the server.

Supporting functions:
1. Automatic compression and decompression: For large files, automatic file compression and decompression operations to improve efficiency.
2. Breakpoint resume: After the upload interruption, the user can continue to upload the file from the last breakpoint to avoid repeated operations.
3. Logging system: Records the download process to provide traceability of user actions.
4. Partial file update: Users can partially update an uploaded file without re-uploading the entire file.
