var easyspear = angular.module('MainApp', ['MainApp.controllers', 'MainApp.services', 'ngRoute', 'wu.masonry', 'ui.bootstrap'])

easyspear.config(['$routeProvider', function($routeProvider) {
		$routeProvider.when('/list', {
			templateUrl: 'static/partials/list.html',
			controller: 'ListController'
		});
		$routeProvider.when('/followed', {
			templateUrl: 'static/partials/followed.html',
			controller: 'FollowController'
		});
		$routeProvider.when('/auction/:name', {
			templateUrl: 'static/partials/auction.html',
			controller: 'AuctionController'
		});
		$routeProvider.otherwise({
			redirectTo:'/list'
		});
}]);


// Filters
easyspear.filter('startFrom', function() {
	return function(input, start) {
		start = +start; //parse to int
		return input.slice(start);
	}
});
// Factories
easyspear.factory('itemFactory', ['$http', function($http) {
	return {
		followToggle : function(item) {
			item.followed = !item.followed; // a white lie
			$http.get("/auction/"+ item.auction_name +"/"+ item.item_id + (item.followed ? "/follow" : "/unfollow")).success(function (data, status) {
				// oh no
			});
			return item;
		},
		updateItems : function(list, item) {
			var ret = []
			for(var i = 0; i < list.length; i++) {
				var each = list[i];
				if(each._id == item._id) {
					ret.push(item);
				} else {
					ret.push(each);
				}	
			}
			return ret;
		}
	}
}]);
	
// Directives
easyspear.directive('scrollTrigger', function($window) {
	return {
		link : function(scope, element, attrs) {
			var offset = parseInt(attrs.threshold) || 0;
			var e = jQuery(element[0]);
			var doc = jQuery(document);
			angular.element(document).bind('scroll', function() {
				if (doc.scrollTop() + $window.innerHeight + offset > e.offset().top) {
					scope.$apply(attrs.scrollTrigger);
				}
			});
		}
	}
});
easyspear.directive('timeAgo', ['NotificationService',
function(NotificationService) {
    return {
        template: '<span>{{timeAgo}}</span>',
        replace: true,
        link: function(scope, element, attrs) {
            var updateTime = function() {
                scope.timeAgo = moment(scope.$eval(attrs.timeAgo)).fromNow();
            }
            NotificationService.onTimeAgo(scope, updateTime); // subscribe
            updateTime();
        }
    }
}])
