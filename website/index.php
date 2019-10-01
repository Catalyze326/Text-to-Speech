<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <!--Import Google Icon Font-->
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <!--Import materialize.css-->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>

    <link rel="stylesheet" href="style.css">
    <title>Text To Speech</title>
</head>
<body>
<h2 class="centerHor">Upload a text file you want to have turned into audio</h2>
<h4 class="centerHor">The file must be less than 2MB</h4>

<form class="center" action="" method="post" enctype="multipart/form-data">
    <div class="file-field input-field">
        <div class="btn">
            <span>File</span>
            <input type="file" name="fileToUpload">
        </div>
        <div class="file-path-wrapper">
            <input class="file-path validate" type="text" placeholder="Upload a file">
        </div>
    </div>
    <div>
        <button class="btn waves-effect waves-light" type="submit" value="Upload Image" name="submit">Upload File
            <i class="material-icons right"></i>
        </button>
    </div>

</form>

<?php
if (isset($_POST['submit'])) {
    session_start();
    $id = rand(100000000, 999999999);
    $target_dir = "uploads/";
    $target_file = $target_dir . $id;
    $imageFileType = strtolower(pathinfo($_FILES["fileToUpload"]["name"], PATHINFO_EXTENSION));
    $uploadOk = true;
    if ($imageFileType == "jpg" || $imageFileType == "png" || $imageFileType == "jpeg"
        || $imageFileType == "gif" || $imageFileType == "tif" || $imageFileType == "raw" || $imageFileType == "pdf"
        || $imageFileType == "txt" || $imageFileType == "docx") {
    } else {
        echo "<div class=\"error\">Sorry, only PDF, PNG, JPG, TIF, RAW, PDF, TXT and DOCX files are allowed.</div>";
        $uploadOk = false;
    }
    if ($uploadOk)
        if (move_uploaded_file($_FILES["fileToUpload"]["tmp_name"], $target_file)) {
            echo "<div class=\"error\">The file " . basename($_FILES["fileToUpload"]["name"]) . " has been uploaded.</div>";
        } else {
            echo "<div class=\"error\">Sorry, there was an error uploading your file.</div>";
        }
    while (!file_exists("uploads/$id")) {
        sleep(1);
    }
    echo "<audio src=\"uploads/$id\"></audio>";
    echo "<a href=\"uploads/$id\">Download</a>";
}
?>


</body>
</html>