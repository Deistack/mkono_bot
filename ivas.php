<?php
// ivas.php
require_once __DIR__ . "/config.php";

function ivas_cookie_header() {
    global $IVAS_COOKIES;
    $parts = [];
    foreach ($IVAS_COOKIES as $k => $v) {
        $parts[] = $k . "=" . $v;
    }
    return implode("; ", $parts);
}

function ivas_request($url, $post = null) {
    global $IVAS_BASE;
    $ch = curl_init($url);
    $headers = [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:159.0) Gecko/20100101 Firefox/159.0",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie: " . ivas_cookie_header(),
    ];
    if ($post !== null) {
        $headers[] = "Content-Type: application/x-www-form-urlencoded; charset=UTF-8";
        $headers[] = "X-Requested-With: XMLHttpRequest";
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($post));
    }
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);
    $resp = curl_exec($ch);
    curl_close($ch);
    return $resp;
}

function ivas_csrf() {
    global $IVAS_BASE;
    $html = ivas_request($IVAS_BASE . "/portal/sms/received");
    if (preg_match('/name="_token"\s+value="([^"]+)"/', $html, $m)) {
        return $m[1];
    }
    if (preg_match('/value="([^"]+)"\s+name="_token"/', $html, $m)) {
        return $m[1];
    }
    return null;
}

function ivas_check_otps($from = "", $to = "") {
    $token = ivas_csrf();
    if (!$token) return null;
    global $IVAS_BASE;
    $html = ivas_request($IVAS_BASE . "/portal/sms/received/getsms", [
        "from" => $from,
        "to" => $to,
        "_token" => $token,
    ]);
    // parse ranges
    preg_match_all('/class="col-sm-4"[^>]*>\s*(.*?)\s*</s', $html, $ranges);
    $details = [];
    foreach ($ranges[1] as $r) {
        $r = trim(strip_tags($r));
        if ($r !== "") $details[] = ["country_number" => $r];
    }
    return ["raw" => $html, "sms_details" => $details, "csrf" => $token];
}

function ivas_numbers($range, $from = "", $to = "") {
    $token = ivas_csrf();
    if (!$token) return [];
    global $IVAS_BASE;
    $html = ivas_request($IVAS_BASE . "/portal/sms/received/getsms/number", [
        "_token" => $token,
        "start" => $from,
        "end" => $to,
        "range" => $range,
    ]);
    preg_match_all('/col-sm-4[^>]*>\s*(\+?\d+)\s*</', $html, $nums);
    $out = [];
    foreach ($nums[1] as $n) {
        $out[] = trim($n);
    }
    return $out;
}

function ivas_otp($phone, $range, $from = "", $to = "") {
    $token = ivas_csrf();
    if (!$token) return null;
    global $IVAS_BASE;
    $html = ivas_request($IVAS_BASE . "/portal/sms/received/getsms/number/sms", [
        "_token" => $token,
        "start" => $from,
        "end" => $to,
        "Number" => $phone,
        "Range" => $range,
    ]);
    if (preg_match('/col-9 col-sm-6[^>]*>\s*<p[^>]*>\s*(.*?)\s*<\/p>/s', $html, $m)) {
        return trim(strip_tags($m[1]));
    }
    return null;
}
"