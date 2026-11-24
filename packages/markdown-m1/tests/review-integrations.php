<?php
function review_integrations_seed(): array {
    $form=WPCF7_ContactForm::get_template();$form->set_title('Review form');
    $properties=$form->get_properties();$properties['form']='<label>Name [text* your-name]</label><label>Email [email* your-email]</label>[textarea your-message][submit "Send"]<script>window.reviewFormExecuted=1</script>';
    $properties['mail']['sender']='Review <review@example.invalid>';$properties['mail']['recipient']='destination@example.invalid';$properties['mail']['subject']='[your-name]';$properties['mail']['body']='[your-message]';$properties['additional_settings']='skip_mail: on';
    $form->set_properties($properties);$form->save();
    $table=TablePress::$model_table->get_table_template();$table['name']='Review table';$table['data']=[['機器','電圧'],['PLC','24 V']];$tableId=TablePress::$model_table->add($table);if(is_wp_error($tableId))throw new RuntimeException($tableId->get_error_message());
    $receipt=Flamingo_Inbound_Message::add(['posted_data_hash'=>hash('sha256',uniqid()),'subject'=>'Review inquiry','from'=>'Review <reader@example.invalid>','fields'=>['message'=>'技術資料についての問い合わせ']]);
    $user=wp_insert_user(['user_login'=>'review-reader-'.bin2hex(random_bytes(3)),'user_pass'=>'Isolated-only-123!','user_email'=>'reader@example.invalid','role'=>'subscriber','first_name'=>'Technical']);
    if(is_wp_error($user))throw new RuntimeException($user->get_error_message());update_user_meta($user,'active',1);
    $group=acf_update_field_group(['key'=>'group_review_safe','title'=>'Technical information','fields'=>[],'location'=>[[['param'=>'post_type','operator'=>'==','value'=>'page']]]]);
    acf_update_field(['key'=>'field_review_safe_voltage','name'=>'review_voltage','label'=>'Voltage','type'=>'text','parent'=>$group['ID']]);
    $page=wp_insert_post(['post_type'=>'page','post_title'=>'ACF review','post_status'=>'publish']);update_field('field_review_safe_voltage','24 V',$page);
    return ['form'=>$form->id(),'sender'=>$properties['mail']['sender'],'table'=>$tableId,'table_data'=>$table['data'],'receipt'=>$receipt->id(),'login'=>get_userdata($user)->user_login,'prepared'=>get_option('wpmembers_settings'),'acf_page'=>$page];
}
function review_integrations_check(array $ids): void {
    $form=WPCF7_ContactForm::get_instance($ids['form']);$p=$form->get_properties();
    review_assert($p['mail']['sender']===$ids['sender']&&$p['mail']['body']==='[your-message]','CF7 mail placeholders/address changed');
    review_assert(str_contains($p['form'],'[text* your-name]'),'CF7 input grammar lost');
    review_assert(!str_contains($p['form'],'<script>'),'Unsafe CF7 form executed');
    $table=TablePress::$model_table->load((string)$ids['table'],true,true);review_assert(!is_wp_error($table)&&$table['data']===$ids['table_data'],'Table cells changed');
    review_assert(get_post_meta($ids['receipt'],'_field_message',true)==='技術資料についての問い合わせ','Receipt body lost');
    review_assert(get_post_meta($ids['receipt'],'_from',true)==='Review <reader@example.invalid>','Flamingo sender address lost');
    $notes=[];$shortcode=$form->shortcode();
    review_assert(OzekiResilience\M1\RecoveryContent::html($shortcode,'form-reference',$notes)===$shortcode,'Generated CF7 reference disabled');
    $user=get_user_by('login',$ids['login']);review_assert($user&&wp_check_password('Isolated-only-123!',$user->user_pass,$user->ID),'Member login lost');
    $settings=get_option('wpmembers_settings');foreach(['version','db_version','form_tags'] as $k)review_assert($settings[$k]===$ids['prepared'][$k],'Prepared member runtime changed');
    review_assert(get_field('review_voltage',$ids['acf_page'])==='24 V','ACF field value/definition lost');
}
