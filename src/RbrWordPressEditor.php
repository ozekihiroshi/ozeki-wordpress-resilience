<?php
declare(strict_types=1);
namespace Owr;
/** Explicit opt-in editor for the already enrolled three-page projection. */
final class RbrWordPressEditor
{
    public static function boot(array $ids): void {
        $allowed=static function()use($ids):bool{
            foreach($ids as $id)if(!current_user_can('edit_post',$id)||!current_user_can('publish_pages'))return false;
            return true;
        };
        add_action('load-post.php',static function()use($ids,$allowed){
            $id=(int)($_POST['post_ID']??$_GET['post']??0);
            if(!in_array($id,$ids,true))return;
            if(!$allowed())wp_die('この3ページを編集する権限がありません。','',403);
            if(($_SERVER['REQUEST_METHOD']??'GET')!=='GET'||($_GET['action']??'')!=='edit')wp_die('S3先行保存の編集画面を使用してください。','',409);
            wp_safe_redirect(admin_url('admin.php?page=owr-protected-editor&post='.$id));exit;
        });
        add_action('admin_menu',static function()use($ids,$allowed){
            add_submenu_page('','S3先行保存','S3先行保存','publish_pages','owr-protected-editor',static function()use($ids,$allowed){
                if(!$allowed())wp_die('この3ページを編集する権限がありません。','',403);
                $role=array_search((int)($_GET['post']??0),$ids,true);
                if($role===false)wp_die('登録されたページを選択してください。','',400);
                echo '<style>#owr-editor [hidden]{display:none!important}</style><div class="wrap" id="owr-editor"><h1>S3先行保存 — ページ編集</h1><p>本文・タイトル・スラッグを変更できます。画像とページ間の関係は維持します。S3確定後にのみ公開内容へ反映します。</p>';
                echo '<p role="status" aria-live="polite" id="owr-status">状態を確認中です。</p><p id="owr-generation"></p><form id="owr-form"><fieldset id="owr-fields" disabled>';
                echo '<p><label>タイトル<br><input id="owr-title" class="large-text" required maxlength="200"></label></p><p><label>スラッグ<br><input id="owr-slug" required pattern="[a-z0-9-]{1,100}"></label></p><p>本文（段落単位・HTMLやブロック機能なし）</p><div id="owr-paragraphs"></div><button type="button" id="owr-add" class="button">段落を追加</button></fieldset><p><button type="submit" class="button button-primary" id="owr-save" disabled>S3へ保存して反映</button> <button type="button" class="button" id="owr-resume" hidden>同じ保存を再開</button> <button type="button" class="button" id="owr-reload">最新状態を読み直す</button></p></form><p>この試作画面は登録済み3固定ページ専用です。通常投稿・新規画像登録・Markdown・予約公開には対応しません。</p></div>';
                $config=['role'=>$role,'nonce'=>wp_create_nonce('wp_rest'),'api'=>rest_url('owr-rbr/v1/')];
                echo '<script>window.owrEditorConfig='.wp_json_encode($config,JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT).';</script>';
                echo '<script>'.file_get_contents(__DIR__.'/../assets/rbr-editor.js').'</script>';
            });
        });
    }
}
