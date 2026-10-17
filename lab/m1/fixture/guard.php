<?php
/** Test-only controls and a deterministic local contact form. */
add_filter('pre_http_request', static fn () => new WP_Error('owr_external_disabled', 'External HTTP disabled.'), PHP_INT_MIN);
add_filter('pre_wp_mail', static fn () => false, PHP_INT_MIN);
add_filter('automatic_updater_disabled', '__return_true');
add_shortcode('owr_contact', static function (): string {
    return '<form method="post" action="' . esc_url(admin_url('admin-post.php')) . '">'
        . '<input type="hidden" name="action" value="owr_fixture_contact">'
        . wp_nonce_field('owr_fixture_contact', '_wpnonce', true, false)
        . '<label>Test message <input name="message" required></label><button>Send test</button></form>';
});
$handler = static function (): void {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || ! wp_verify_nonce($_POST['_wpnonce'] ?? '', 'owr_fixture_contact')) {
        status_header(403); echo 'OWR_FORM_REJECTED'; exit;
    }
    $message = sanitize_text_field(wp_unslash($_POST['message'] ?? ''));
    if ($message !== 'OWR-SYNTHETIC-INQUIRY') { status_header(400); echo 'OWR_FORM_INVALID'; exit; }
    // No mail, external service, or personal-data persistence.
    status_header(200); header('Content-Type: text/plain; charset=UTF-8'); echo 'OWR_FORM_ACCEPTED'; exit;
};
add_action('admin_post_nopriv_owr_fixture_contact', $handler);
add_action('admin_post_owr_fixture_contact', $handler);
