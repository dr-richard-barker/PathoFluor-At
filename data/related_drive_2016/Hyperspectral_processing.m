close all
for e = 1:size(img,3)
    imshow(img(:,:,e),[])
    drawnow
end
%%
close all
for e = 400:600
    imshow(img(:,:,e),[]);
    drawnow
end
%%
close all
imshow(img(:,:,400),[])
%% otsu

close all
midx = [];
for e = 400:600
    t = graythresh(double(img(:,:,400))/255);
    mask = double(img(:,:,e))/255 > t*1.1;
    fidx = find(mask);
    midx = [midx;fidx];
    imshow(mask,[])
    drawnow
end
%%
vec =[];
midx = unique(midx);
cnt = 1;
for e = 400:600
    tmp = img(:,:,e);
    vec(:,cnt) = tmp(midx);
    cnt = cnt + 1;
end
%%
[c,s,l,t,e,m] = pca(vec,'NumComponents',3);
%%
sz = size(img);
rimg = reshape(img,[sz(1)*sz(2) sz(3)]);
rimg = rimg(:,400:600);
%%
cen = bsxfun(@minus,rimg,m);
nimg = cen*c;
kidx = kmeans(nimg,2);
mask = reshape(kidx,[sz(1) sz(2)]);
nimg = reshape(nimg,[sz(1) sz(2) 3]);
%%
imshow(nimg,[])
figure;
imshow(mask==2,[]);
%% sample plants
fidx = find(mask==2);

pvec =[];
cnt = 1;
for e = 400:600
    tmp = img(:,:,e);
    pvec(:,cnt) = tmp(fidx);
    cnt = cnt + 1;
end
%%
[pc,ps,pl,pt,pe,pm] = pca(pvec,'NumComponents',3);
%%
Z = zeros([size(mask) 3]);
for e = 1:size(Z,3)
    tmp = Z(:,:,e);
    tmp(fidx) = ps(:,e);
    Z(:,:,e) = tmp;
end