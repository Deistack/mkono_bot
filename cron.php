<?php
// cron.php - run via cPanel cron every minute
require_once __DIR__ . "/config.php";
require_once __DIR__ . "/ivas.php";

function tg_send($chat_id, $text) {
    global $TELEGRAM_BOT_TOKEN;
    if (empty($chat_id) || empty($TELEGRAM_BOT_TOKEN)) return;
    $url = "https://api.telegram.org/bot" . $TELEGRAM_BOT_TOKEN . "/sendMessage";
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
        "chat_id" => $chat_id,
        "text" => $text,
    ]));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_exec($ch);
    curl_close($ch);
}

$seen = [];
if (file_exists($SEEN_FILE)) {
    $seen = array_filter(array_map("trim", file($SEEN_FILE)));
}
$seen_map = array_flip($seen);

$res = ivas_check_otps("", "");
if (!$res) exit;

// try to get numbers and otps for each range
foreach ($res["sms_details"] as $d) {
    $range = $d["country_number"];
    $nums = ivas_numbers($range, "", "");
    foreach ($nums as $num) {
        $otp = ivas_otp($num, $range, "", "");
        if (!$otp) continue;
        $key = $num . "|" . $otp;
        if (isset($seen_map[$key])) continue;
        $seen_map[$key] = true;
        $seen[] = $key;
        $msg = "🔐 New OTP Received\n\n🔢 OTP: " . $otp . "\n📱 Number: " . $num . "\n🌐 Range: " . $range . "\n⏰ Time: " . date("H:i:s");
        tg_send($TELEGRAM_GROUP_CHAT_ID, $msg);
    }
}

file_put_contents($SEEN_FILE, implode("\n", $seen) . "\n");
"