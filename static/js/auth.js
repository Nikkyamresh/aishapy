$(function() {
  $('a#calculate').bind('click', function() {
    send();
    return false;
  });
  $("#form").bind('submit',function() {
    send();
    return false;
  })

});
function send() {
  window.location="/auth?psd="+$('input[name="psd"]').val();
  return false;
}
