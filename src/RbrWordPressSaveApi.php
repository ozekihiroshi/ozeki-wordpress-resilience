<?php
declare(strict_types=1);
namespace Owr;
/** Explicitly configured opt-in API. Not automatically enabled by the admin ZIP. */
final class RbrWordPressSaveApi
{
    public static function boot(\Closure $factory,array $ids): void {
        add_action('rest_api_init',static function()use($factory,$ids){
            register_rest_route('owr-rbr/v1','/editor',[
                'methods'=>'GET',
                'permission_callback'=>static function()use($ids){
                    if(!is_user_logged_in())return new \WP_Error('owr_auth','Authentication required',['status'=>401]);
                    foreach($ids as $id)if(!current_user_can('edit_post',$id)||!current_user_can('publish_pages'))return new \WP_Error('owr_forbidden','Cannot edit all enrolled pages',['status'=>403]);
                    return true;
                },
                'callback'=>static function()use($factory){
                    try{$r=new \WP_REST_Response($factory()->editorState(),200);$r->header('Cache-Control','no-store');return $r;}
                    catch(\Throwable $e){return new \WP_Error('owr_editor_unavailable','Editor enrollment requires operator review',['status'=>409]);}
                }
            ]);
            register_rest_route('owr-rbr/v1','/save',[
                'methods'=>'POST',
                'permission_callback'=>static function()use($ids){
                    if(!is_user_logged_in())return new \WP_Error('owr_auth','Authentication required',['status'=>401]);
                    foreach($ids as $id)if(!current_user_can('edit_post',$id)||!current_user_can('publish_pages'))return new \WP_Error('owr_forbidden','Cannot edit all enrolled pages',['status'=>403]);
                    return true;
                },
                'callback'=>static function(\WP_REST_Request $request)use($factory){
                    if(strlen($request->get_body())>262144)return new \WP_Error('owr_input','Request too large',['status'=>413]);
                    try{
                        $input=$request->get_json_params();if(!is_array($input))throw new \InvalidArgumentException('JSON object required');
                        return new \WP_REST_Response($factory()->save($input),200);
                    }catch(\InvalidArgumentException $e){return new \WP_Error('owr_input','Unsupported three-page input',['status'=>400]);}
                    catch(\Throwable $e){$code=in_array($e->getMessage(),['Stale generation','Pending save must be reconciled','Operation input conflict','Protected page drift','Superseded operation'],true)?'owr_save_conflict':'owr_save_unresolved';return new \WP_Error($code,'Save not completed. Reconcile the same operation; do not create a replacement operation.',['status'=>409]);}
                }
            ]);
        });
        // Preserve unrelated pages. UI interception alone would not enforce S3-first order.
        add_filter('rest_pre_dispatch',static function($result,$server,$request)use($ids){
            if(in_array($request->get_method(),['GET','HEAD','OPTIONS'],true))return $result;
            if(preg_match('~^/wp/v2/pages/([0-9]+)(?:/|$)~',$request->get_route(),$m)&&in_array((int)$m[1],$ids,true))
                return new \WP_Error('owr_protected_entry','Use the protected save API for this enrolled page',['status'=>409]);
            return $result;
        },10,3);
    }
}
