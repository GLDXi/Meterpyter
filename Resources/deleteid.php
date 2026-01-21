<?php
	if ($_SERVER["REQUEST_METHOD"] === "GET"){
		$deleteid = $_GET['deleteid'];
		system("rm -rf /var/www/html/meterpyter/ransomware/ID/${deleteid}");
	}
?>
