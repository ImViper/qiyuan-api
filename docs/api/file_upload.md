文件 API

Gemini 系列人工智能 (AI) 模型专为处理各种类型的输入数据（包括文本、图片和音频）而设计。由于这些模型可以处理多种类型或模式的数据，因此 Gemini 模型被称为多模态模型，或被描述为具有多模态功能。

本指南介绍了如何使用 Files API 处理媒体文件。音频文件、图片、视频、文档和其他受支持的文件类型的基本操作相同。

如需了解文件提示指南，请参阅文件提示指南部分。

上传文件
您可以使用 Files API 上传媒体文件。如果请求总大小（包括文件、文本提示、系统说明等）超过 20 MB，请始终使用 Files API。

以下代码会上传文件，然后在调用 generateContent 时使用该文件。

Python
JavaScript
Go
REST

file, err := client.UploadFileFromPath(ctx, "path/to/sample.mp3", nil)
if err != nil {
    log.Fatal(err)
}
defer client.DeleteFile(ctx, file.Name)

model := client.GenerativeModel("gemini-2.0-flash")
resp, err := model.GenerateContent(ctx,
    genai.FileData{URI: file.URI},
    genai.Text("Describe this audio clip"))
if err != nil {
    log.Fatal(err)
}

printResponse(resp)
获取文件的元数据
您可以调用 files.get 来验证 API 是否已成功存储上传的文件并获取其元数据。

Python
JavaScript
Go
REST

file, err := client.UploadFileFromPath(ctx, "path/to/sample.mp3", nil)
if err != nil {
    log.Fatal(err)
}

gotFile, err := client.GetFile(ctx, file.Name)
if err != nil {
    log.Fatal(err)
}
fmt.Println("Got file:", gotFile.Name)
列出已上传的文件
您可以使用 Files API 上传多个文件。以下代码会获取上传的所有文件的列表：

Python
JavaScript
Go
REST

iter := client.ListFiles(ctx)
for {
    ifile, err := iter.Next()
    if err == iterator.Done {
        break
    }
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(ifile.Name)
}
删除已上传的文件
文件会在 48 小时后自动删除。您也可以手动删除上传的文件：

Python
JavaScript
Go
REST

file, err := client.UploadFileFromPath(ctx, "path/to/sample.mp3", nil)
if err != nil {
    log.Fatal(err)
}
client.DeleteFile(ctx, file.Name)
使用情况信息
您可以使用 Files API 上传媒体文件并与其互动。借助 Files API，您最多可为每个项目存储 20 GB 的文件，每个文件的大小上限为 2 GB。文件会存储 48 小时。在此期间，您可以使用 API 获取文件的元数据，但无法下载文件。Files API 在已推出 Gemini API 的所有地区均可免费使用。