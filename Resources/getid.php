<?php
	if ($_SERVER["REQUEST_METHOD"] === "GET") {
		$id = $_GET['getkey'];
		echo file_get_contents("ID/${id}/infos.txt");
	}
?>
