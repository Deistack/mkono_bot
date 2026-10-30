<?php
// index.php - simple dashboard
require_once __DIR__ . "/config.php";
require_once __DIR__ . "/ivas.php";
$r = ivas_check_otps("", "");
?>
<!doctype html>
<html>
<head><meta charset="utf-8"><title>IVAS Bot</title></head>
<body>
<h1>IVAS OTP Bot</h1>
<p>Ranges:</p>
<ul>
<?php foreach ($r["sms_details"] as $d): ?>
<li><?php echo htmlspecialchars($d["country_number"]); ?></li>
<?php endforeach; ?>
</ul>
</body>
</html>
"