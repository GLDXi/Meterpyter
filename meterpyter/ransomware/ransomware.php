<?php
	if ($_SERVER["REQUEST_METHOD"] === "GET") {
		$id = $_GET['id'];
		system("python3 keygen.py $id");
		echo file_get_contents("ID/${id}/infos.txt");
	}
?>
